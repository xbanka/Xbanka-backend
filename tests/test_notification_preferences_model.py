"""Storage for notification preferences. Nothing reads these yet - the
enforcement in new_notification and the endpoints come next - so these tests
pin the shape: defaults on, one row per category, and rows tied to the user."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.enums import NotificationCategoryEnum
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notification_preferences import NotificationPreference
from app.models.notification_settings import NotificationSettings
from app.models.role import Role


@pytest.fixture
def staff(db_session) -> ERPUser:
    role = Role(name="Support")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    staff = ERPUser(
        first_name="Pref",
        last_name="Staff",
        email="prefs@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def test_staff_start_with_no_rows(db_session, staff):
    """No row means enabled, so existing staff need no backfill."""
    assert staff.notification_settings is None
    assert staff.notification_preferences == []


def test_channel_switches_default_to_on(db_session, staff):
    db_session.add(NotificationSettings(user_id=staff.id))
    db_session.commit()
    db_session.refresh(staff)

    assert staff.notification_settings.in_app_enabled is True
    assert staff.notification_settings.email_enabled is True


def test_category_toggles_default_to_on(db_session, staff):
    db_session.add(
        NotificationPreference(
            user_id=staff.id, category=NotificationCategoryEnum.RATE_MANAGEMENT
        )
    )
    db_session.commit()

    (preference,) = staff.notification_preferences
    assert preference.category == NotificationCategoryEnum.RATE_MANAGEMENT
    assert preference.in_app is True
    assert preference.email is True


def test_one_row_per_category_per_staff_member(db_session, staff):
    db_session.add_all(
        [
            NotificationPreference(
                user_id=staff.id,
                category=NotificationCategoryEnum.RATE_MANAGEMENT,
                email=False,
            ),
            NotificationPreference(
                user_id=staff.id,
                category=NotificationCategoryEnum.APPROVAL_REQUESTS,
                in_app=False,
            ),
        ]
    )
    db_session.commit()

    stored = {p.category: p for p in staff.notification_preferences}
    assert stored[NotificationCategoryEnum.RATE_MANAGEMENT].email is False
    assert stored[NotificationCategoryEnum.RATE_MANAGEMENT].in_app is True
    assert stored[NotificationCategoryEnum.APPROVAL_REQUESTS].in_app is False

    db_session.add(
        NotificationPreference(
            user_id=staff.id, category=NotificationCategoryEnum.RATE_MANAGEMENT
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_every_category_in_the_design_is_storable(db_session, staff):
    db_session.add_all(
        NotificationPreference(user_id=staff.id, category=category)
        for category in NotificationCategoryEnum
    )
    db_session.commit()

    assert len(staff.notification_preferences) == len(NotificationCategoryEnum) == 7
