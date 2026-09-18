"""Reading a notification marks it read; it must never cancel an action the
notification still offers (regression: reading a role-change prompt used to
resolve it, hiding the Confirm button while the change was still pending)."""

import pytest

from app.core.enums import (
    NotificationReferenceTypeEnum,
    NotificationStatusEnum,
    RoleChangeStatusEnum,
)
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.role import Role
from app.models.role_change_log import RoleChangeLog
from app.services.auth import AuthService


def _make_role(db_session, name: str) -> Role:
    role = Role(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


def _make_staff(db_session, role: Role, email: str) -> ERPUser:
    staff = ERPUser(
        first_name="Test",
        last_name="Staff",
        email=email,
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


@pytest.fixture
def target(db_session) -> ERPUser:
    viewer = _make_role(db_session, "Viewer")
    _make_role(db_session, "Manager")
    return _make_staff(db_session, viewer, "read.target@example.com")


def _add_notification(db_session, user, reference_type, reference_id) -> Notification:
    notif = Notification(
        user_id=user.id,
        message="Something happened.",
        reference_type=reference_type,
        reference_id=reference_id,
        status=NotificationStatusEnum.ACTIVE,
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)
    return notif


def _add_role_change(db_session, staff, requested_by, status) -> RoleChangeLog:
    role_change = RoleChangeLog(
        staff_id=staff.id,
        requested_by_id=requested_by.id,
        previous_role="Viewer",
        new_role="Manager",
        status=status,
    )
    db_session.add(role_change)
    db_session.commit()
    db_session.refresh(role_change)
    return role_change


def _mark_read(test_client, staff, notification_id):
    return test_client.patch(
        f"/api/erp/notifications/{notification_id}/mark-as-read", headers=_headers(staff)
    )


def _status(db_session, notification_id) -> NotificationStatusEnum:
    db_session.expire_all()
    return db_session.get(Notification, notification_id).status


def test_reading_a_pending_role_change_prompt_keeps_it_actionable(
    test_client, db_session, verified_superadmin, target
):
    propose = test_client.patch(
        f"/api/staff/{target.id}/roles-permissions",
        json={"role": "Manager"},
        headers=_headers(verified_superadmin),
    )
    assert propose.status_code == 200
    role_change_id = propose.json()["role_change_id"]

    db_session.expire_all()
    prompt = (
        db_session.query(Notification)
        .filter(Notification.user_id == target.id)
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert str(prompt.reference_id) == role_change_id

    response = _mark_read(test_client, target, prompt.id)

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    # still actionable: the change has not been confirmed yet
    assert _status(db_session, prompt.id) == NotificationStatusEnum.ACTIVE

    confirm = test_client.post(
        f"/api/audit/role-changes/{role_change_id}/confirm", headers=_headers(target)
    )
    assert confirm.status_code == 200
    assert _status(db_session, prompt.id) == NotificationStatusEnum.RESOLVED


def test_reading_a_settled_role_change_prompt_resolves_it(
    test_client, db_session, verified_superadmin, target
):
    role_change = _add_role_change(
        db_session, target, verified_superadmin, RoleChangeStatusEnum.CONFIRMED
    )
    notif = _add_notification(
        db_session, target, NotificationReferenceTypeEnum.STAFF_ACCOUNT, role_change.id
    )

    assert _mark_read(test_client, target, notif.id).status_code == 200
    assert _status(db_session, notif.id) == NotificationStatusEnum.RESOLVED


def test_requesters_copy_resolves_even_while_the_change_is_pending(
    test_client, db_session, verified_superadmin, target
):
    """The requester is notified with the same reference_id, but the change is
    not theirs to confirm, so reading it resolves normally."""
    role_change = _add_role_change(
        db_session, target, verified_superadmin, RoleChangeStatusEnum.PENDING
    )
    notif = _add_notification(
        db_session,
        verified_superadmin,
        NotificationReferenceTypeEnum.STAFF_ACCOUNT,
        role_change.id,
    )

    assert _mark_read(test_client, verified_superadmin, notif.id).status_code == 200
    assert _status(db_session, notif.id) == NotificationStatusEnum.RESOLVED


def test_reading_an_account_notification_resolves_it(test_client, db_session, target):
    """A password/profile notification points at the staff member, not a role
    change, so there is nothing to keep open."""
    notif = _add_notification(
        db_session, target, NotificationReferenceTypeEnum.STAFF_ACCOUNT, target.id
    )

    assert _mark_read(test_client, target, notif.id).status_code == 200
    assert _status(db_session, notif.id) == NotificationStatusEnum.RESOLVED


def test_reading_a_rate_proposal_notification_keeps_it_active(
    test_client, db_session, target
):
    notif = _add_notification(
        db_session, target, NotificationReferenceTypeEnum.RATE_PROPOSAL, target.id
    )

    assert _mark_read(test_client, target, notif.id).status_code == 200
    assert _status(db_session, notif.id) == NotificationStatusEnum.ACTIVE


def test_another_users_notification_is_not_found(
    test_client, db_session, verified_superadmin, target
):
    notif = _add_notification(
        db_session, target, NotificationReferenceTypeEnum.STAFF_ACCOUNT, target.id
    )

    response = _mark_read(test_client, verified_superadmin, notif.id)

    assert response.status_code == 404
    assert _status(db_session, notif.id) == NotificationStatusEnum.ACTIVE
