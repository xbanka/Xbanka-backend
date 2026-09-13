import pytest

from app.core.enums import EmailTypeEnum
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.role import Role
from app.services.auth import AuthService

URL = "/api/auth/erp/change-password"
CURRENT_PASSWORD = "@Password123"
NEW_PASSWORD = "N3w@Password!"


@pytest.fixture(autouse=True)
def send_email(mocker):
    """Keep the security-alert email off the network; TestClient runs
    background tasks, so an unpatched send would reach Resend."""
    return mocker.patch("app.api.v1.routes.auth.erp.send_password_changed_email")


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


def _password_notifications(db_session, staff: ERPUser):
    db_session.expire_all()
    return (
        db_session.query(Notification)
        .filter(
            Notification.user_id == staff.id,
            Notification.message.like("Your password was changed%"),
        )
        .all()
    )


def test_change_password_success(test_client, db_session, staff, send_email):
    response = test_client.post(URL, json=_payload(), headers=_headers(staff))

    assert response.status_code == 200
    assert response.json() == {"message": "Password has been changed successfully"}
    assert _login(test_client, staff, NEW_PASSWORD).status_code == 200
    assert _login(test_client, staff, CURRENT_PASSWORD).status_code == 401


def test_success_sends_email_and_in_app_notification(
    test_client, db_session, staff, send_email
):
    response = test_client.post(URL, json=_payload(), headers=_headers(staff))
    assert response.status_code == 200

    send_email.assert_called_once()
    kwargs = send_email.call_args.kwargs
    assert kwargs["recipient"] == staff.email
    assert kwargs["email_type"] == EmailTypeEnum.erp
    assert kwargs["reset_url"].endswith("/forgot-password")

    (notification,) = _password_notifications(db_session, staff)
    assert notification.reference_id == staff.id
    assert notification.is_read is False


def test_wrong_current_password_rejected(test_client, db_session, staff, send_email):
    response = test_client.post(
        URL, json=_payload(current="@WrongPass1"), headers=_headers(staff)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect."
    assert _login(test_client, staff, CURRENT_PASSWORD).status_code == 200
    send_email.assert_not_called()
    assert _password_notifications(db_session, staff) == []


def test_mismatched_confirmation_rejected(test_client, staff, send_email):
    response = test_client.post(
        URL, json=_payload(confirm="@SomethingElse1"), headers=_headers(staff)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match"
    send_email.assert_not_called()


def test_weak_new_password_rejected(test_client, db_session, staff, send_email):
    response = test_client.post(URL, json=_payload(new="weak"), headers=_headers(staff))

    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"]
    assert _login(test_client, staff, CURRENT_PASSWORD).status_code == 200
    send_email.assert_not_called()
    assert _password_notifications(db_session, staff) == []


def test_reusing_current_password_rejected(test_client, staff, send_email):
    response = test_client.post(
        URL, json=_payload(new=CURRENT_PASSWORD), headers=_headers(staff)
    )

    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]
    send_email.assert_not_called()


def test_requires_authentication(test_client, staff, send_email):
    response = test_client.post(URL, json=_payload())

    assert response.status_code == 401
    send_email.assert_not_called()
