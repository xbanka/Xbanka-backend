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
    assert staff_client.get("/api/bills/margins").status_code == 403
    assert staff_client.get("/api/bills/margins/history").status_code == 403
    assert (
        staff_client.put(
            "/api/bills/margins/CABLE_TV", json={"isActive": False, "reason": "Pause"}
        ).status_code
        == 403
    )


def test_create_route_is_gone(super_client):
    response = super_client.post(
        "/api/bills/margins",
        json={
            "product": "CABLE_TV",
            "marginType": "FIXED",
            "marginValue": 10,
            "reason": "Launch",
        },
    )

    assert response.status_code == 405


def test_get_margins(mocker, super_client):
    payload = {"data": [{"product": "CABLE_TV", "sampleOn1000": 100}]}
    mocked = mocker.patch(f"{SERVICE}.get_bill_margins", return_value=payload)

    response = super_client.get("/api/bills/margins")

    assert response.status_code == 200
    assert response.json() == payload
    mocked.assert_called_once_with()


def test_update_margin_uses_signed_in_email(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin", return_value={"ok": True})

    response = super_client.put(
        "/api/bills/margins/CABLE_TV",
        json={
            "marginType": "PERCENTAGE",
            "marginValue": 3,
            "reason": "Move to 3%",
            # a client-supplied changedBy must be ignored
            "changedBy": "someone.else@example.com",
        },
    )

    assert response.status_code == 200
    mocked.assert_called_once_with(
        "CABLE_TV",
        {
            "marginType": "PERCENTAGE",
            "marginValue": 3.0,
            "reason": "Move to 3%",
            "changedBy": "superadmin1@xbankang.com",
        },
    )


def test_update_margin_sends_only_given_fields(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin", return_value={"ok": True})

    response = super_client.put(
        "/api/bills/margins/ELECTRICITY", json={"marginValue": 150, "reason": "Raise fee"}
    )

    assert response.status_code == 200
    mocked.assert_called_once_with(
        "ELECTRICITY",
        {"marginValue": 150.0, "reason": "Raise fee", "changedBy": "superadmin1@xbankang.com"},
    )


def test_update_margin_can_switch_off(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin", return_value={})

    response = super_client.put(
        "/api/bills/margins/BETTING", json={"isActive": False, "reason": "Pause"}
    )

    assert response.status_code == 200
    assert mocked.call_args.args[1]["isActive"] is False


def test_fixed_margin_may_exceed_100(mocker, super_client):
    mocker.patch(f"{SERVICE}.update_bill_margin", return_value={})

    response = super_client.put(
        "/api/bills/margins/CABLE_TV",
        json={"marginType": "FIXED", "marginValue": 250, "reason": "Flat fee"},
    )

    assert response.status_code == 200


def test_update_margin_validation(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.update_bill_margin")
    url = "/api/bills/margins/CABLE_TV"

    for body in (
        # nothing to change
        {"reason": "No change"},
        # bad margin type
        {"marginType": "FLAT", "reason": "Bad type"},
        # negative value
        {"marginValue": -1, "reason": "Negative"},
        # percentage above 100 when the type is sent too
        {"marginType": "PERCENTAGE", "marginValue": 120, "reason": "Too high"},
        # short reason
        {"isActive": True, "reason": "ab"},
        # missing reason
        {"isActive": True},
    ):
        assert super_client.put(url, json=body).status_code == 422, body

    mocked.assert_not_called()


@pytest.mark.parametrize("product", ["AIRTIME", "DATA", "WATER"])
def test_products_without_margins_are_rejected(mocker, super_client, product):
    update = mocker.patch(f"{SERVICE}.update_bill_margin")
    history = mocker.patch(f"{SERVICE}.get_bill_margin_history")

    put = super_client.put(
        f"/api/bills/margins/{product}", json={"isActive": True, "reason": "Nope"}
    )
    get = super_client.get(f"/api/bills/margins/history?product={product}")

    assert put.status_code == 422
    assert get.status_code == 422
    update.assert_not_called()
    history.assert_not_called()


def test_history_passes_filters(mocker, super_client):
    mocked = mocker.patch(
        f"{SERVICE}.get_bill_margin_history", return_value={"items": [], "total": 0}
    )

    response = super_client.get("/api/bills/margins/history?product=CABLE_TV&page=2")

    assert response.status_code == 200
    mocked.assert_called_once_with(product="CABLE_TV", page=2)


def test_history_without_filters(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.get_bill_margin_history", return_value={})

    assert super_client.get("/api/bills/margins/history").status_code == 200
    mocked.assert_called_once_with(product=None, page=1)


def test_core_errors_pass_through(mocker, super_client):
    mocker.patch(
        "requests.request",
        return_value=_mock_response(
            409, text='{"message":"Margin was changed by someone else"}'
        ),
    )

    response = super_client.put(
        "/api/bills/margins/CABLE_TV", json={"isActive": False, "reason": "Pause"}
    )

    assert response.status_code == 409
    assert "changed by someone else" in response.json()["detail"]


def test_service_hits_core_endpoints(mocker):
    from app.services.internal_backend import InternalAPIService

    request = mocker.patch(
        "requests.request", return_value=_mock_response(200, {"data": []})
    )

    InternalAPIService.get_bill_margins()
    InternalAPIService.update_bill_margin("CABLE_TV", {"isActive": False})
    InternalAPIService.get_bill_margin_history(product=None, page=1)

    calls = [(c.args[0], c.args[1].split("/internal", 1)[1]) for c in request.call_args_list]
    assert calls == [
        ("GET", "/bills/margins"),
        ("PUT", "/bills/margins/CABLE_TV"),
        ("GET", "/bills/margins/history"),
    ]
    # None params are dropped, so an unfiltered history sends only the page
    assert request.call_args_list[2].kwargs["params"] == {"page": 1}
