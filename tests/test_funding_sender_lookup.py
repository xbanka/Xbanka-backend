from unittest.mock import MagicMock

import pytest
import requests

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.role import Role
from app.services.auth import AuthService

SERVICE = "app.services.internal_backend.InternalAPIService"
URL = "/api/transactions/funding/lookup"

MATCH = {
    "fundingAccountId": "7c0c1d2e-5b4a-4c53-9d57-0f3f0f4a1b11",
    "bank": "Paycom (Opay)",
    "accountName": "OMOLADE OLUWASEGUN AKANBI",
    "customer": {
        "userId": "991fbf45-8c5a-4840-9f4f-8af81c586922",
        "xbId": "XB123",
        "email": "customer@example.com",
        "isActive": True,
        "name": "Omolade Akanbi",
    },
    "wallet": {"currency": "NGN"},
}


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
    """A signed-in staff member with no permissions."""
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
    assert test_client.get(f"{URL}?accountNumber=0123456789").status_code == 401


def test_staff_without_permission_is_forbidden(mocker, staff_client):
    mocked = mocker.patch(f"{SERVICE}.find_funding_account_owner")

    assert staff_client.get(f"{URL}?accountNumber=0123456789").status_code == 403
    mocked.assert_not_called()


def test_lookup_returns_matches(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.find_funding_account_owner", return_value=[MATCH])

    response = super_client.get(f"{URL}?accountNumber=7054178290&bankCode=100004")

    assert response.status_code == 200
    assert response.json() == [MATCH]
    mocked.assert_called_once_with("7054178290", "100004")


def test_bank_code_is_optional(mocker, super_client):
    mocked = mocker.patch(f"{SERVICE}.find_funding_account_owner", return_value=[])

    response = super_client.get(f"{URL}?accountNumber=7054178290")

    assert response.status_code == 200
    assert response.json() == []
    mocked.assert_called_once_with("7054178290", None)


@pytest.mark.parametrize(
    "query",
    [
        "",  # accountNumber is required
        "?accountNumber=12345",  # too short
        "?accountNumber=12345678901",  # too long
        "?accountNumber=12345abcde",  # not digits
        "?accountNumber=7054178290&bankCode=",  # empty bank code
    ],
)
def test_invalid_query_is_rejected(mocker, super_client, query):
    mocked = mocker.patch(f"{SERVICE}.find_funding_account_owner")

    assert super_client.get(f"{URL}{query}").status_code == 422
    mocked.assert_not_called()


def test_core_errors_pass_through(mocker, super_client):
    mocker.patch(
        "requests.request",
        return_value=_mock_response(401, text='{"message":"Invalid or missing internal API key"}'),
    )

    response = super_client.get(f"{URL}?accountNumber=7054178290")

    assert response.status_code == 401
    assert "internal API key" in response.json()["detail"]


def test_service_calls_core_lookup_and_drops_empty_bank_code(mocker):
    from app.services.internal_backend import InternalAPIService

    request = mocker.patch("requests.request", return_value=_mock_response(200, []))

    InternalAPIService.find_funding_account_owner("7054178290")
    InternalAPIService.find_funding_account_owner("7054178290", "100004")

    first, second = request.call_args_list
    assert first.args[0] == "GET"
    assert first.args[1].endswith("/internal/funding/lookup")
    assert first.kwargs["params"] == {"accountNumber": "7054178290"}
    assert second.kwargs["params"] == {"accountNumber": "7054178290", "bankCode": "100004"}
