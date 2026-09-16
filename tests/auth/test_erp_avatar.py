import pytest

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.role import Role
from app.services.auth import AuthService
from app.utils.s3_utils import MAX_IMAGE_BYTES

URL = "/api/erp/me/avatar"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def staff(db_session) -> ERPUser:
    role = Role(name="Support")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    staff = ERPUser(
        first_name="Ada",
        last_name="Obi",
        email="avatar.staff@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
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


def _upload(test_client, staff, name="me.png", data=PNG_BYTES, content_type="image/png"):
    return test_client.post(
        URL, files={"avatar": (name, data, content_type)}, headers=_headers(staff)
    )


def _reload(db_session, staff: ERPUser) -> ERPUser:
    db_session.expire_all()
    return db_session.get(ERPUser, staff.id)


def test_upload_stores_avatar_path(test_client, db_session, staff):
    response = _upload(test_client, staff)

    assert response.status_code == 200
    avatar_url = response.json()["avatar_url"]
    assert avatar_url.startswith(f"avatars/{staff.id}_")
    assert avatar_url.endswith(".png")
    assert _reload(db_session, staff).avatar_url == avatar_url
    assert test_client.get("/api/erp/me", headers=_headers(staff)).json()["avatar_url"] == avatar_url


def test_each_upload_replaces_the_previous_path(test_client, db_session, staff):
    first = _upload(test_client, staff).json()["avatar_url"]
    second = _upload(test_client, staff, name="new.jpg", content_type="image/jpeg").json()["avatar_url"]

    assert first != second  # unique key per upload, so caches don't serve the old image
    assert second.endswith(".jpg")
    assert _reload(db_session, staff).avatar_url == second


@pytest.mark.parametrize(
    "name,content_type",
    [
        ("doc.pdf", "application/pdf"),  # allowed for payout attachments, not avatars
        ("script.svg", "image/svg+xml"),
        ("me.png", "application/pdf"),   # extension and content type disagree
        ("me.txt", "text/plain"),
    ],
)
def test_rejects_non_image_uploads(test_client, db_session, staff, name, content_type):
    response = _upload(test_client, staff, name=name, content_type=content_type)

    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]
    assert _reload(db_session, staff).avatar_url is None


def test_rejects_oversized_image(test_client, db_session, staff):
    too_big = b"\x89PNG\r\n\x1a\n" + b"0" * MAX_IMAGE_BYTES

    response = _upload(test_client, staff, data=too_big)

    assert response.status_code == 400
    assert response.json()["detail"] == "Image is too large. The limit is 5MB"
    assert _reload(db_session, staff).avatar_url is None


def test_upload_sends_in_app_notification(test_client, db_session, staff):
    _upload(test_client, staff)

    db_session.expire_all()
    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == staff.id,
            Notification.message == "Your profile picture has been updated.",
        )
        .all()
    )

    assert len(notifications) == 1
    assert notifications[0].reference_id == staff.id
    assert notifications[0].is_read is False


def test_rejected_upload_sends_no_notification(test_client, db_session, staff):
    response = _upload(test_client, staff, name="doc.pdf", content_type="application/pdf")

    assert response.status_code == 400
    db_session.expire_all()
    assert (
        db_session.query(Notification).filter(Notification.user_id == staff.id).count()
        == 0
    )


def test_requires_authentication(test_client, staff):
    response = test_client.post(URL, files={"avatar": ("me.png", PNG_BYTES, "image/png")})

    assert response.status_code == 401
