import pytest

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.role import Role
from app.services.auth import AuthService

URL = "/api/erp/me"
PROFILE_UPDATED = "Your profile details have been updated."


@pytest.fixture
def staff(db_session) -> ERPUser:
    role = Role(name="Support")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    staff = ERPUser(
        first_name="Ada",
        last_name="Obi",
        email="ada.obi@example.com",
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


def _reload(db_session, staff: ERPUser) -> ERPUser:
    db_session.expire_all()
    return db_session.get(ERPUser, staff.id)


def _profile_notifications(db_session, staff: ERPUser):
    db_session.expire_all()
    return (
        db_session.query(Notification)
        .filter(Notification.user_id == staff.id, Notification.message == PROFILE_UPDATED)
        .all()
    )


def test_updates_names_and_phone(test_client, db_session, staff):
    response = test_client.patch(
        URL,
        json={"first_name": "  Adaeze ", "last_name": "Okafor", "phone": "08031234567"},
        headers=_headers(staff),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Adaeze"  # trimmed
    assert body["last_name"] == "Okafor"
    assert body["phone"] == "+2348031234567"  # stored in E.164
    assert "pending_role_change" in body  # same shape as GET /me

    saved = _reload(db_session, staff)
    assert (saved.first_name, saved.last_name, saved.phone) == (
        "Adaeze",
        "Okafor",
        "+2348031234567",
    )
    assert test_client.get(URL, headers=_headers(staff)).json()["phone"] == "+2348031234567"


def test_partial_update_leaves_other_fields_alone(test_client, db_session, staff):
    response = test_client.patch(URL, json={"last_name": "Eze"}, headers=_headers(staff))

    assert response.status_code == 200
    saved = _reload(db_session, staff)
    assert (saved.first_name, saved.last_name, saved.phone) == ("Ada", "Eze", None)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("08031234567", "+2348031234567"),       # Nigerian, local format
        ("+234 803 123 4567", "+2348031234567"),  # Nigerian, international format
        ("0701-234-5678", "+2347012345678"),      # separators allowed
        ("+234(0)8031234567", "+2348031234567"),  # trunk prefix in brackets
        ("  080 3123 4567  ", "+2348031234567"),  # spaces and padding
        ("+44 7911 123456", "+447911123456"),     # UK mobile
        ("+1 (415) 555-2671", "+14155552671"),    # US
    ],
)
def test_accepts_nigerian_and_international_numbers(test_client, staff, raw, expected):
    response = test_client.patch(URL, json={"phone": raw}, headers=_headers(staff))

    assert response.status_code == 200
    assert response.json()["phone"] == expected


@pytest.mark.parametrize(
    "raw",
    [
        "12345",                 # too short for any Nigerian number
        "+1",                    # country code with no number
        "0803123",               # only long enough for a local number
        "not-a-number",
        "+234 803 123 45678",    # right shape, no such Nigerian range
        "+999 1234567",          # no such country code
        # phonenumbers.parse() alone accepts all of these: it strips junk
        # around the number and maps keypad letters onto digits.
        "abc08031234567",
        "08031234567xyz",
        "0803-FLOWERS",
        "+1-800-FLOWERS",
        "<08031234567>",
        "e00023244aa",
        "08031234567;DROP",
    ],
)
def test_rejects_invalid_phone_numbers(test_client, db_session, staff, raw):
    response = test_client.patch(URL, json={"phone": raw}, headers=_headers(staff))

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid phone number")
    assert _reload(db_session, staff).phone is None


@pytest.mark.parametrize("cleared", [None, "", "   "])
def test_phone_can_be_cleared(test_client, db_session, staff, cleared):
    staff.phone = "+2348031234567"
    db_session.commit()

    response = test_client.patch(URL, json={"phone": cleared}, headers=_headers(staff))

    assert response.status_code == 200
    assert response.json()["phone"] is None
    assert _reload(db_session, staff).phone is None


@pytest.mark.parametrize("value", [None, "", "   "])
def test_names_cannot_be_blank(test_client, db_session, staff, value):
    response = test_client.patch(URL, json={"first_name": value}, headers=_headers(staff))

    assert response.status_code == 400
    assert response.json()["detail"] == "First name cannot be empty."
    assert _reload(db_session, staff).first_name == "Ada"


def test_name_length_is_limited(test_client, staff):
    response = test_client.patch(URL, json={"last_name": "x" * 101}, headers=_headers(staff))

    assert response.status_code == 400
    assert response.json()["detail"] == "Last name must be at most 100 characters."


def test_empty_body_rejected(test_client, staff):
    response = test_client.patch(URL, json={}, headers=_headers(staff))

    assert response.status_code == 400
    assert "at least one" in response.json()["detail"]


def test_fields_outside_the_schema_rejected(test_client, db_session, staff):
    response = test_client.patch(
        URL, json={"email": "new@example.com"}, headers=_headers(staff)
    )

    assert response.status_code == 422
    assert _reload(db_session, staff).email == "ada.obi@example.com"


def test_change_sends_one_in_app_notification(test_client, db_session, staff):
    test_client.patch(URL, json={"phone": "08031234567"}, headers=_headers(staff))

    (notification,) = _profile_notifications(db_session, staff)
    assert notification.reference_id == staff.id
    assert notification.is_read is False


def test_no_op_update_sends_no_notification(test_client, db_session, staff):
    response = test_client.patch(
        URL, json={"first_name": "Ada", "last_name": "Obi"}, headers=_headers(staff)
    )

    assert response.status_code == 200
    assert _profile_notifications(db_session, staff) == []


def test_requires_authentication(test_client, staff):
    response = test_client.patch(URL, json={"first_name": "Mallory"})

    assert response.status_code == 401
