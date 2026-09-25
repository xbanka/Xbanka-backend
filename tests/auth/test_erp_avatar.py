import pytest
from botocore.exceptions import ClientError

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.role import Role
from app.services.auth import AuthService
from app.utils.s3_utils import MAX_IMAGE_BYTES
from app.utils.settings import settings

URL = "/api/erp/me/avatar"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class FakeS3:
    """Records avatar uploads and deletes, so no test reaches AWS."""

    def __init__(self):
        self.uploads: list[dict] = []
        self.deletes: list[dict] = []

    def upload(self, file, bucket, object_name=None, content_type=None):
        self.uploads.append(
            {
                "bucket": bucket,
                "key": object_name,
                "content_type": content_type,
                "body": file.read(),
            }
        )

    def delete(self, bucket, object_name):
        self.deletes.append({"bucket": bucket, "key": object_name})


@pytest.fixture(autouse=True)
def s3(monkeypatch) -> FakeS3:
    fake = FakeS3()

    monkeypatch.setattr("app.services.erp_user.S3_BUCKET_AVATARS", "test-avatars")
    monkeypatch.setattr(settings, "S3_BUCKET_AVATARS", "test-avatars")
    monkeypatch.setattr("app.services.erp_user.upload_file", fake.upload)
    monkeypatch.setattr("app.services.erp_user.delete_file", fake.delete)
    monkeypatch.setattr(
        "app.schemas.erp.user.get_image_url",
        lambda key, bucket: f"https://signed.test/{bucket}/{key}",
    )
    return fake


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


def test_upload_sends_file_to_avatars_bucket(test_client, staff, s3):
    avatar_url = _upload(test_client, staff).json()["avatar_url"]

    assert s3.uploads == [
        {
            "bucket": "test-avatars",
            "key": avatar_url,
            "content_type": "image/png",
            "body": PNG_BYTES,
        }
    ]
    assert s3.deletes == []  # nothing to replace on a first upload


def test_response_includes_signed_url(test_client, staff):
    uploaded = _upload(test_client, staff).json()
    expected = f"https://signed.test/test-avatars/{uploaded['avatar_url']}"

    assert uploaded["avatar_signed_url"] == expected
    me = test_client.get("/api/erp/me", headers=_headers(staff)).json()
    assert me["avatar_signed_url"] == expected


def test_no_signed_url_without_an_avatar(test_client, staff):
    me = test_client.get("/api/erp/me", headers=_headers(staff)).json()

    assert me["avatar_url"] is None
    assert me["avatar_signed_url"] is None


def test_no_signed_url_when_bucket_not_configured(test_client, staff, monkeypatch):
    avatar_url = _upload(test_client, staff).json()["avatar_url"]
    monkeypatch.setattr(settings, "S3_BUCKET_AVATARS", "")

    me = test_client.get("/api/erp/me", headers=_headers(staff)).json()

    assert me["avatar_url"] == avatar_url
    assert me["avatar_signed_url"] is None


def test_failed_s3_upload_returns_500_and_changes_nothing(
    test_client, db_session, staff, monkeypatch
):
    def failing_upload(*args, **kwargs):
        raise ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "PutObject")

    monkeypatch.setattr("app.services.erp_user.upload_file", failing_upload)

    response = _upload(test_client, staff)

    assert response.status_code == 500
    assert response.json()["detail"] == "An error occurred uploading your profile picture"
    assert _reload(db_session, staff).avatar_url is None
    assert db_session.query(Notification).filter(Notification.user_id == staff.id).count() == 0


def test_each_upload_replaces_the_previous_path(test_client, db_session, staff):
    first = _upload(test_client, staff).json()["avatar_url"]
    second = _upload(test_client, staff, name="new.jpg", content_type="image/jpeg").json()["avatar_url"]

    assert first != second  # unique key per upload, so caches don't serve the old image
    assert second.endswith(".jpg")
    assert _reload(db_session, staff).avatar_url == second


def test_second_upload_deletes_the_previous_object(test_client, staff, s3):
    first = _upload(test_client, staff).json()["avatar_url"]
    _upload(test_client, staff, name="new.jpg", content_type="image/jpeg")

    assert s3.deletes == [{"bucket": "test-avatars", "key": first}]


def test_failed_delete_of_previous_object_does_not_fail_the_request(
    test_client, db_session, staff, s3, monkeypatch
):
    _upload(test_client, staff)

    def failing_delete(*args, **kwargs):
        raise ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "DeleteObject")

    monkeypatch.setattr("app.services.erp_user.delete_file", failing_delete)
    response = _upload(test_client, staff, name="new.jpg", content_type="image/jpeg")

    assert response.status_code == 200
    assert _reload(db_session, staff).avatar_url == response.json()["avatar_url"]


@pytest.mark.parametrize(
    "name,content_type",
    [
        ("doc.pdf", "application/pdf"),  # allowed for payout attachments, not avatars
        ("script.svg", "image/svg+xml"),
        ("me.png", "application/pdf"),   # extension and content type disagree
        ("me.txt", "text/plain"),
    ],
)
def test_rejects_non_image_uploads(test_client, db_session, staff, s3, name, content_type):
    response = _upload(test_client, staff, name=name, content_type=content_type)

    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]
    assert _reload(db_session, staff).avatar_url is None
    assert s3.uploads == []


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
