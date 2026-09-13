import pytest

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.role import Role
from app.services.auth import AuthService

URL = "/api/auth/erp/change-password"
CURRENT_PASSWORD = "@Password123"
NEW_PASSWORD = "N3w@Password!"


@pytest.fixture
def staff(db_session) -> ERPUser:
    role = Role(name="Support")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    staff = ERPUser(
        first_name="Pass",
        last_name="Word",
        email="password.change@example.com",
        hashed_password=Hasher.get_password_hash(CURRENT_PASSWORD),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _headers(staff: ERPUser) -> dict:
    token = AuthService.create_access_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    return {"Authorization": f"Bearer {token}"}


def _payload(current=CURRENT_PASSWORD, new=NEW_PASSWORD, confirm=None) -> dict:
    return {
        "current_password": current,
        "new_password": new,
        "confirm_password": new if confirm is None else confirm,
    }


def _login(test_client, staff: ERPUser, password: str):
    return test_client.post(
        "/api/auth/erp/login", json={"email": staff.email, "password": password}
    )


def test_change_password_success(test_client, staff):
    response = test_client.post(URL, json=_payload(), headers=_headers(staff))

    assert response.status_code == 200
    assert response.json() == {"message": "Password has been changed successfully"}
    assert _login(test_client, staff, NEW_PASSWORD).status_code == 200
    assert _login(test_client, staff, CURRENT_PASSWORD).status_code == 401


def test_wrong_current_password_rejected(test_client, staff):
    response = test_client.post(
        URL, json=_payload(current="@WrongPass1"), headers=_headers(staff)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect."
    assert _login(test_client, staff, CURRENT_PASSWORD).status_code == 200


def test_mismatched_confirmation_rejected(test_client, staff):
    response = test_client.post(
        URL, json=_payload(confirm="@SomethingElse1"), headers=_headers(staff)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match"


def test_weak_new_password_rejected(test_client, staff):
    response = test_client.post(URL, json=_payload(new="weak"), headers=_headers(staff))

    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"]
    assert _login(test_client, staff, CURRENT_PASSWORD).status_code == 200


def test_reusing_current_password_rejected(test_client, staff):
    response = test_client.post(
        URL, json=_payload(new=CURRENT_PASSWORD), headers=_headers(staff)
    )

    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]


def test_requires_authentication(test_client, staff):
    response = test_client.post(URL, json=_payload())

    assert response.status_code == 401
