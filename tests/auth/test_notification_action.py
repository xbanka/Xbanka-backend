"""The notifications list carries a derived `action`, so the panel knows which
notification offers a Confirm button instead of guessing from reference_type
(which is STAFF_ACCOUNT for password, profile, avatar and role-change alike)."""

import pytest

from app.core.enums import NotificationReferenceTypeEnum, NotificationStatusEnum
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.role import Role
from app.services.auth import AuthService


def _make_role(db_session, name: str) -> Role:
    role = Role(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


def _headers(staff: ERPUser) -> dict:
    token = AuthService.create_access_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def target(db_session) -> ERPUser:
    viewer = _make_role(db_session, "Viewer")
    _make_role(db_session, "Manager")
    staff = ERPUser(
        first_name="Test",
        last_name="Staff",
        email="action.target@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=viewer.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _propose(test_client, requester, target) -> str:
    response = test_client.patch(
        f"/api/staff/{target.id}/roles-permissions",
        json={"role": "Manager"},
        headers=_headers(requester),
    )
    assert response.status_code == 200
    return response.json()["role_change_id"]


def _notifications(test_client, staff) -> list[dict]:
    response = test_client.get("/api/erp/notifications", headers=_headers(staff))
    assert response.status_code == 200
    return response.json()


def _add_account_notification(db_session, staff) -> Notification:
    notif = Notification(
        user_id=staff.id,
        message="Your password was changed.",
        reference_type=NotificationReferenceTypeEnum.STAFF_ACCOUNT,
        reference_id=staff.id,
        status=NotificationStatusEnum.ACTIVE,
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()
    return notif


def test_role_change_prompt_carries_a_confirm_action(
    test_client, db_session, verified_superadmin, target
):
    _add_account_notification(db_session, target)
    role_change_id = _propose(test_client, verified_superadmin, target)

    by_action = {
        str(n["reference_id"]): n["action"] for n in _notifications(test_client, target)
    }

    assert by_action[role_change_id] == {
        "type": "CONFIRM_ROLE_CHANGE",
        "role_change_id": role_change_id,
    }
    # same reference_type, but nothing to do about it
    assert by_action[str(target.id)] is None


def test_action_survives_marking_the_prompt_as_read(
    test_client, db_session, verified_superadmin, target
):
    role_change_id = _propose(test_client, verified_superadmin, target)
    prompt = next(
        n
        for n in _notifications(test_client, target)
        if str(n["reference_id"]) == role_change_id
    )

    read = test_client.patch(
        f"/api/erp/notifications/{prompt['id']}/mark-as-read", headers=_headers(target)
    )
    assert read.status_code == 200

    after = next(
        n
        for n in _notifications(test_client, target)
        if str(n["reference_id"]) == role_change_id
    )
    assert after["is_read"] is True
    assert after["status"] == "ACTIVE"
    assert after["action"]["role_change_id"] == role_change_id


def test_action_disappears_once_confirmed(
    test_client, db_session, verified_superadmin, target
):
    role_change_id = _propose(test_client, verified_superadmin, target)

    confirm = test_client.post(
        f"/api/audit/role-changes/{role_change_id}/confirm", headers=_headers(target)
    )
    assert confirm.status_code == 200

    prompt = next(
        n
        for n in _notifications(test_client, target)
        if str(n["reference_id"]) == role_change_id
    )
    assert prompt["action"] is None
    assert prompt["status"] == "RESOLVED"


def test_action_disappears_once_superseded(
    test_client, db_session, verified_superadmin, target
):
    _make_role(db_session, "Auditor")
    first_id = _propose(test_client, verified_superadmin, target)

    second = test_client.patch(
        f"/api/staff/{target.id}/roles-permissions",
        json={"role": "Auditor"},
        headers=_headers(verified_superadmin),
    )
    second_id = second.json()["role_change_id"]

    by_action = {
        str(n["reference_id"]): n["action"] for n in _notifications(test_client, target)
    }
    assert by_action[first_id] is None  # superseded, no longer confirmable
    assert by_action[second_id]["role_change_id"] == second_id


def test_requester_sees_no_action_on_their_copy(
    test_client, db_session, verified_superadmin, target
):
    """The requester is notified when the change is confirmed, carrying the same
    reference_id - but it is not theirs to confirm."""
    role_change_id = _propose(test_client, verified_superadmin, target)
    test_client.post(
        f"/api/audit/role-changes/{role_change_id}/confirm", headers=_headers(target)
    )

    for notif in _notifications(test_client, verified_superadmin):
        assert notif["action"] is None
