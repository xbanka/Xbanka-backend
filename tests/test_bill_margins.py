from unittest.mock import MagicMock

import pytest
import requests

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.role import Role
from app.services.auth import AuthService

SERVICE = "app.services.internal_backend.InternalAPIService"


def _mock_response(status_code=200, json_data=None, text="error"):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    response.text = text
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(str(status_code))
    return response


@pytest.fixture
def staff_client(test_client, db_session):
    """A signed-in staff member whose role is not Super Admin."""
    role = Role(name="Operations")
    db_session.add(role)
    db_session.commit()
    staff = ERPUser(
        first_name="Ops",
        last_name="Staff",
        email="ops@xbankang.com",
        hashed_password=Hasher.get_password_hash("@OpsStaff123"),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()
    token = AuthService.create_access_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


def test_requires_auth(test_client):
    assert test_client.get("/api/bills/margins").status_code == 401


def test_non_super_admin_is_forbidden(staff_client):
    erp_client = staff_client
    assert erp_client.get("/api/bills/margins").status_code == 403
    assert erp_client.get("/api/bills/margins/history").status_code == 403
    assert (
        erp_client.post(
            "/api/bills/margins",
            json={
                "product": "DATA",
                "marginType": "FIXED",
                "marginValue": 10,
                "reason": "Launch",
            },
        ).status_code
        == 403
    )
    assert (
        erp_client.put(
            "/api/bills/margins/DATA", json={"isActive": False, "reason": "Pause"}
        ).status_code
        == 403
    )


def test_get_margins(mocker, super_client):
    payload = {"data": [{"product": "DATA", "configured": False}]}
    mocked = mocker.patch(f"{SERVICE}.get_bill_margins", return_value=payload)

    response = super_client.get("/api/bills/margins")

    assert response.status_code == 200
    assert response.json() == payload
    mocked.assert_called_once_with()


def test_create_margin_uses_signed_in_email(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.create_bill_margin", return_value={"ok": True})

    response = super_client.post(
        "/api/bills/margins",
        json={
            "product": "AIRTIME",
            "marginType": "FIXED",
            "marginValue": 15,
            "isActive": True,
            "reason": "Launch margin",
            # a client-supplied changedBy must be ignored
            "changedBy": "someone.else@example.com",
        },
    )

    assert response.status_code == 200
    mocked.assert_called_once_with(
        {
            "product": "AIRTIME",
            "marginType": "FIXED",
            "marginValue": 15.0,
            "isActive": True,
            "reason": "Launch margin",
            "changedBy": "superadmin1@xbankang.com",
        }
    )


def test_create_margin_defaults_inactive(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.create_bill_margin", return_value={})

    super_client.post(
        "/api/bills/margins",
        json={
            "product": "DATA",
            "marginType": "PERCENTAGE",
            "marginValue": 3,
            "reason": "Launch",
        },
    )

    assert mocked.call_args.args[0]["isActive"] is False


def test_create_margin_validation(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.create_bill_margin")
    base = {"product": "DATA", "marginType": "PERCENTAGE", "marginValue": 3, "reason": "Launch"}

    for override in (
        {"product": "WATER"},
        {"marginType": "FLAT"},
        {"marginValue": -1},
        {"marginValue": 101},
        {"reason": "ab"},
    ):
        response = super_client.post("/api/bills/margins", json={**base, **override})
        assert response.status_code == 422, override

    mocked.assert_not_called()


def test_fixed_margin_may_exceed_100(mocker, super_client):
    mocker.patch(f"{SERVICE}.create_bill_margin", return_value={})

    response = super_client.post(
        "/api/bills/margins",
        json={"product": "CABLE_TV", "marginType": "FIXED", "marginValue": 250, "reason": "Flat fee"},
    )

    assert response.status_code == 200


def test_update_margin_sends_only_given_fields(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin", return_value={"ok": True})

    response = super_client.put(
        "/api/bills/margins/DATA", json={"marginValue": 3, "reason": "Raise to 3%"}
    )

    assert response.status_code == 200
    mocked.assert_called_once_with(
        "DATA",
        {"marginValue": 3.0, "reason": "Raise to 3%", "changedBy": "superadmin1@xbankang.com"},
    )


def test_update_margin_can_switch_off(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin", return_value={})

    response = super_client.put(
        "/api/bills/margins/BETTING", json={"isActive": False, "reason": "Pause"}
    )

    assert response.status_code == 200
    assert mocked.call_args.args[1]["isActive"] is False


def test_update_margin_validation(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin")

    # nothing to change
    assert (
        super_client.put("/api/bills/margins/DATA", json={"reason": "No change"}).status_code
        == 422
    )
    # unknown product
    assert (
        super_client.put(
            "/api/bills/margins/WATER", json={"isActive": True, "reason": "Nope"}
        ).status_code
        == 422
    )
    # percentage above 100 when the type is sent too
    assert (
        super_client.put(
            "/api/bills/margins/DATA",
            json={"marginType": "PERCENTAGE", "marginValue": 120, "reason": "Too high"},
        ).status_code
        == 422
    )
    # short reason
    assert (
        super_client.put(
            "/api/bills/margins/DATA", json={"isActive": True, "reason": "ab"}
        ).status_code
        == 422
    )

    mocked.assert_not_called()


def test_history_passes_filters(mocker, super_client):
    mocked = mocker.patch(
        f"{SERVICE}.get_bill_margin_history", return_value={"items": [], "total": 0}
    )

    response = super_client.get("/api/bills/margins/history?product=DATA&page=2")

    assert response.status_code == 200
    mocked.assert_called_once_with(product="DATA", page=2)


def test_history_rejects_unknown_product(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.get_bill_margin_history")

    assert super_client.get("/api/bills/margins/history?product=WATER").status_code == 422
    mocked.assert_not_called()


def test_core_errors_pass_through(mocker, super_client):
    mocker.patch(
        "requests.request",
        return_value=_mock_response(409, text='{"message":"Margin already exists"}'),
    )

    response = super_client.post(
        "/api/bills/margins",
        json={"product": "DATA", "marginType": "FIXED", "marginValue": 5, "reason": "Again"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_service_hits_core_endpoints(mocker):
    from app.services.internal_backend import InternalAPIService

    request = mocker.patch(
        "requests.request", return_value=_mock_response(200, {"data": []})
    )

    InternalAPIService.get_bill_margins()
    InternalAPIService.update_bill_margin("DATA", {"isActive": False})
    InternalAPIService.get_bill_margin_history(product=None, page=1)

    calls = [(c.args[0], c.args[1].split("/internal", 1)[1]) for c in request.call_args_list]
    assert calls == [
        ("GET", "/bills/margins"),
        ("PUT", "/bills/margins/DATA"),
        ("GET", "/bills/margins/history"),
    ]
    # None params are dropped, so an unfiltered history sends only the page
    assert request.call_args_list[2].kwargs["params"] == {"page": 1}
