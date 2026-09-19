"""GET/PATCH /erp/me/notification-preferences.

Nothing enforces these yet - new_notification still fans out to everyone - so
these tests pin the contract the settings page relies on: a complete response
every time, and partial updates that leave untouched toggles alone."""

import pytest

from app.core.enums import NotificationCategoryEnum
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notification_preferences import DEFAULT_NOTIFICATION_PREFERENCES
from app.models.role import Role
from app.services.auth import AuthService

URL = "/api/erp/me/notification-preferences"
ALL_ON = {"in_app": True, "email": True}


@pytest.fixture
def staff(db_session) -> ERPUser:
    role = Role(name="Support")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    staff = ERPUser(
        first_name="Pref",
        last_name="Staff",
        email="prefs.api@example.com",
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


def _get(test_client, staff):
    response = test_client.get(URL, headers=_headers(staff))
    assert response.status_code == 200
    return response.json()


def _patch(test_client, staff, payload):
    return test_client.patch(URL, json=payload, headers=_headers(staff))


def test_defaults_match_the_design(test_client, staff):
    """Everything in-app; email only where it is worth an inbox interruption."""
    body = _get(test_client, staff)

    assert body["channels"] == ALL_ON
    assert set(body["categories"]) == {c.value for c in NotificationCategoryEnum}
    assert all(toggles["in_app"] for toggles in body["categories"].values())

    email_on = {c for c, toggles in body["categories"].items() if toggles["email"]}
    assert email_on == {"SUPPORT_ACTIVITY", "SYSTEM_SECURITY"}


def test_defaults_come_from_the_map(test_client, staff):
    """The response is the map, so editing it moves anyone without a row."""
    body = _get(test_client, staff)

    assert body["categories"] == {
        category.value: dict(defaults)
        for category, defaults in DEFAULT_NOTIFICATION_PREFERENCES.items()
    }


def test_creating_a_row_keeps_the_other_toggle_at_its_default(test_client, staff):
    """Changing one toggle must not silently flip the other to the column
    default - the new row is seeded from the map first."""
    response = _patch(
        test_client, staff, {"categories": {"SUPPORT_ACTIVITY": {"in_app": False}}}
    )

    assert response.status_code == 200
    # email stays True because SUPPORT_ACTIVITY defaults to True, not because
    # of the column default
    assert response.json()["categories"]["SUPPORT_ACTIVITY"] == {
        "in_app": False,
        "email": True,
    }


def test_channel_switch_can_be_turned_off(test_client, staff):
    response = _patch(test_client, staff, {"channels": {"email": False}})

    assert response.status_code == 200
    assert response.json()["channels"] == {"in_app": True, "email": False}
    # persisted, not just echoed
    assert _get(test_client, staff)["channels"] == {"in_app": True, "email": False}


def test_category_toggle_can_be_turned_off(test_client, staff):
    response = _patch(
        test_client, staff, {"categories": {"RATE_MANAGEMENT": {"in_app": False}}}
    )

    assert response.status_code == 200
    categories = response.json()["categories"]
    assert categories["RATE_MANAGEMENT"] == {"in_app": False, "email": False}
    # untouched, still at its default
    assert categories["APPROVAL_REQUESTS"] == {"in_app": True, "email": False}


def test_updates_accumulate(test_client, staff):
    _patch(test_client, staff, {"categories": {"RATE_MANAGEMENT": {"email": False}}})
    _patch(test_client, staff, {"categories": {"RATE_MANAGEMENT": {"in_app": False}}})
    _patch(test_client, staff, {"channels": {"in_app": False}})

    body = _get(test_client, staff)
    assert body["channels"] == {"in_app": False, "email": True}
    assert body["categories"]["RATE_MANAGEMENT"] == {"in_app": False, "email": False}


def test_several_categories_in_one_request(test_client, staff):
    response = _patch(
        test_client,
        staff,
        {
            "channels": {"in_app": True, "email": False},
            "categories": {
                "SUPPORT_ACTIVITY": {"in_app": False, "email": False},
                "SYSTEM_SECURITY": {"email": False},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["channels"] == {"in_app": True, "email": False}
    assert body["categories"]["SUPPORT_ACTIVITY"] == {"in_app": False, "email": False}
    assert body["categories"]["SYSTEM_SECURITY"] == {"in_app": True, "email": False}


def test_toggles_are_per_staff_member(test_client, db_session, staff, verified_superadmin):
    _patch(test_client, staff, {"channels": {"in_app": False}})

    assert _get(test_client, verified_superadmin)["channels"] == ALL_ON


@pytest.mark.parametrize(
    "payload",
    [
        {},                                             # nothing to change
        {"channels": {}},                               # ditto
        {"categories": {}},                             # ditto
        {"categories": {"RATE_MANAGEMENT": {}}},        # ditto
    ],
)
def test_empty_updates_rejected(test_client, staff, payload):
    response = _patch(test_client, staff, payload)

    assert response.status_code == 400
    assert "at least one" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {"categories": {"NOT_A_CATEGORY": {"in_app": False}}},
        {"channels": {"sms": False}},
        {"categories": {"RATE_MANAGEMENT": {"push": False}}},
        {"channels": {"in_app": "yes please"}},
    ],
)
def test_invalid_payloads_rejected(test_client, staff, payload):
    assert _patch(test_client, staff, payload).status_code == 422


def test_requires_authentication(test_client, staff):
    assert test_client.get(URL).status_code == 401
    assert test_client.patch(URL, json={"channels": {"email": False}}).status_code == 401
