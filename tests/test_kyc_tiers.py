from unittest.mock import MagicMock

import requests

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.role import Role
from app.services.auth import AuthService

SERVICE = "app.services.internal_backend.InternalAPIService"
URL = "/api/customers/kyc-tiers"

TIERS = {
    "message": "Request successful",
    "details": "",
    "errorGroup": "",
    "data": {
        "currency": "NGN",
        "tiers": [
            {
                "tier": 0,
                "name": "Unverified",
                "requirements": ["Create an account"],
                "dailyLimit": 150000,
                "allowedActions": [],
            },
            {
                "tier": 1,
                "name": "Basic",
                "requirements": ["Verify your BVN"],
                "dailyLimit": 500000,
                "allowedActions": ["WITHDRAWAL"],
            },
        ],
    },
}


def _mock_response(status_code=200, json_data=None, text="error"):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    response.text = text
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(str(status_code))
    return response


def test_requires_auth(test_client):
    assert test_client.get(URL).status_code == 401


def test_staff_without_permission_is_forbidden(mocker, test_client, db_session):
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
    mocked = mocker.patch(f"{SERVICE}.get_kyc_tiers")

    assert test_client.get(URL).status_code == 403
    mocked.assert_not_called()


def test_returns_core_response_unchanged(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.get_kyc_tiers", return_value=TIERS)

    response = super_client.get(URL)

    assert response.status_code == 200
    assert response.json() == TIERS
    mocked.assert_called_once_with()


def test_core_errors_pass_through(mocker, super_client):
    mocker.patch(
        "requests.request",
        return_value=_mock_response(401, text='{"message":"Invalid or missing internal API key"}'),
    )

    response = super_client.get(URL)

    assert response.status_code == 401
    assert "internal API key" in response.json()["detail"]


def test_service_calls_core_kyc_tiers(mocker):
    from app.services.internal_backend import InternalAPIService

    request = mocker.patch("requests.request", return_value=_mock_response(200, TIERS))

    assert InternalAPIService.get_kyc_tiers() == TIERS

    assert request.call_args.args[0] == "GET"
    assert request.call_args.args[1].endswith("/internal/kyc/tiers")
