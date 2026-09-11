from app.core.enums import Permission
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.permission import Permission as PermissionModel
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.services.auth import AuthService


def _make_permission(db_session, permission: Permission) -> PermissionModel:
    row = PermissionModel(name=permission.value, category=permission.value.split(":")[0])
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _make_role(db_session, name: str, allowed=()) -> Role:
    role = Role(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    for perm in allowed:
        db_session.add(RolePermissions(role_id=role.id, permission_id=perm.id))
    db_session.commit()
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
    token = AuthService.create_access_token(data={"sub": str(staff.id), "account_type": "erp"})
    return {"Authorization": f"Bearer {token}"}


def _propose_role_change(test_client, requester, target, new_role_name):
    return test_client.patch(
        f"/api/staff/{target.id}/roles-permissions",
        json={"role": new_role_name},
        headers=_headers(requester),
    )


def test_pending_role_change_blocks_target_from_other_routes(
    test_client, db_session, verified_superadmin
):
    view_staff_list = _make_permission(db_session, Permission.VIEW_STAFF_LIST)
    viewer_role = _make_role(db_session, "Viewer", allowed=[view_staff_list])
    _make_role(db_session, "Manager", allowed=[view_staff_list])
    target = _make_staff(db_session, viewer_role, "target@example.com")

    propose = _propose_role_change(test_client, verified_superadmin, target, "Manager")
    assert propose.status_code == 200
    assert propose.json()["status"] == "PENDING"

    # Blocked from an unrelated endpoint while unconfirmed.
    blocked = test_client.get("/api/staff/all", headers=_headers(target))
    assert blocked.status_code == 423
    assert blocked.json()["detail"] == "ROLE_CHANGE_PENDING_CONFIRMATION"

    # /erp/me stays reachable so the frontend can render the confirmation modal.
    me = test_client.get("/api/erp/me", headers=_headers(target))
    assert me.status_code == 200
    pending = me.json()["pending_role_change"]
    assert pending is not None
    assert pending["new_role"] == "Manager"

    confirm = test_client.post(
        f"/api/audit/role-changes/{propose.json()['role_change_id']}/confirm",
        headers=_headers(target),
    )
    assert confirm.status_code == 200

    db_session.refresh(target)
    assert target.role.name == "Manager"

    # No longer blocked once confirmed (Manager also holds VIEW_STAFF_LIST,
    # so a 403 here would have to be the pending-role-change block, not a
    # permission check).
    unblocked = test_client.get("/api/staff/all", headers=_headers(target))
    assert unblocked.status_code == 200


def test_only_the_affected_staff_member_can_confirm(
    test_client, db_session, verified_superadmin
):
    viewer_role = _make_role(db_session, "Viewer")
    manager_role = _make_role(db_session, "Manager")
    target = _make_staff(db_session, viewer_role, "target2@example.com")
    someone_else = _make_staff(db_session, manager_role, "other@example.com")

    propose = _propose_role_change(test_client, verified_superadmin, target, "Manager")
    role_change_id = propose.json()["role_change_id"]

    denied = test_client.post(
        f"/api/audit/role-changes/{role_change_id}/confirm",
        headers=_headers(someone_else),
    )
    assert denied.status_code == 403


def test_role_changes_list_requires_view_audit_logs_permission(
    test_client, db_session, verified_superadmin
):
    role = _make_role(db_session, "NoPerms")
    staff = _make_staff(db_session, role, "noperm@example.com")

    denied = test_client.get("/api/audit/role-changes", headers=_headers(staff))
    assert denied.status_code == 403

    allowed = test_client.get(
        "/api/audit/role-changes", headers=_headers(verified_superadmin)
    )
    assert allowed.status_code == 200


def test_role_changes_list_reflects_pending_and_confirmed_status(
    test_client, db_session, verified_superadmin
):
    viewer_role = _make_role(db_session, "Viewer")
    target = _make_staff(db_session, viewer_role, "target3@example.com")
    _make_role(db_session, "Manager")

    propose = _propose_role_change(test_client, verified_superadmin, target, "Manager")
    role_change_id = propose.json()["role_change_id"]

    listing = test_client.get(
        "/api/audit/role-changes", headers=_headers(verified_superadmin)
    )
    assert listing.status_code == 200
    row = next(r for r in listing.json() if r["id"] == role_change_id)
    assert row["status"] == "PENDING"
    assert row["role_change"] == {"previous_role": "Viewer", "new_role": "Manager"}
    assert row["staff"]["staff_code"] == target.staff_code

    test_client.post(
        f"/api/audit/role-changes/{role_change_id}/confirm",
        headers=_headers(target),
    )

    listing_after = test_client.get(
        "/api/audit/role-changes", headers=_headers(verified_superadmin)
    )
    row_after = next(r for r in listing_after.json() if r["id"] == role_change_id)
    assert row_after["status"] == "CONFIRMED"
