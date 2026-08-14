from uuid import uuid4

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
        db_session.add(RolePermissions(role_id=role.id, permission_id=perm.id, is_allowed=True))
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


# ---------------------------------------------------------------------------
# require_permissions membership check (regression test: it used to compare
# Permission enum strings against ORM Permission objects and was always
# False, silently denying every non-Super-Admin regardless of their actual
# permissions).
# ---------------------------------------------------------------------------


def test_staff_with_permission_can_access_gated_endpoint(test_client, db_session):
    view_staff_list = _make_permission(db_session, Permission.VIEW_STAFF_LIST)
    role = _make_role(db_session, "Viewer", allowed=[view_staff_list])
    staff = _make_staff(db_session, role, "viewer@example.com")

    response = test_client.get("/api/staff/all", headers=_headers(staff))

    assert response.status_code == 200


def test_staff_without_permission_is_denied(test_client, db_session):
    role = _make_role(db_session, "NoPerms")
    staff = _make_staff(db_session, role, "noperms@example.com")

    response = test_client.get("/api/staff/all", headers=_headers(staff))

    assert response.status_code == 403


def test_super_admin_bypasses_permission_check_without_explicit_grant(
    test_client, verified_superadmin
):
    response = test_client.get("/api/staff/all", headers=_headers(verified_superadmin))

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# update_staff_roles_permissions escalation guards
# ---------------------------------------------------------------------------


def test_cannot_change_own_role_or_permissions(test_client, db_session):
    edit_roles = _make_permission(db_session, Permission.EDIT_STAFF_ROLES)
    role = _make_role(db_session, "RoleManager", allowed=[edit_roles])
    staff = _make_staff(db_session, role, "self-edit@example.com")

    response = test_client.patch(
        f"/api/staff/{staff.id}/roles-permissions",
        json={"role": "RoleManager"},
        headers=_headers(staff),
    )

    assert response.status_code == 403
    assert "own role" in response.json()["detail"].lower()


def test_non_super_admin_cannot_promote_target_to_super_admin(test_client, db_session):
    edit_roles = _make_permission(db_session, Permission.EDIT_STAFF_ROLES)
    manager_role = _make_role(db_session, "RoleManager", allowed=[edit_roles])
    target_role = _make_role(db_session, "Viewer")

    acting_staff = _make_staff(db_session, manager_role, "manager@example.com")
    target_staff = _make_staff(db_session, target_role, "target@example.com")

    response = test_client.patch(
        f"/api/staff/{target_staff.id}/roles-permissions",
        json={"role": "Super Admin"},
        headers=_headers(acting_staff),
    )

    assert response.status_code == 403
    assert "super admin can grant" in response.json()["detail"].lower()


def test_super_admin_can_promote_target_to_super_admin(
    test_client, db_session, verified_superadmin
):
    target_role = _make_role(db_session, "Viewer")
    target_staff = _make_staff(db_session, target_role, "target@example.com")

    response = test_client.patch(
        f"/api/staff/{target_staff.id}/roles-permissions",
        json={"role": "Super Admin"},
        headers=_headers(verified_superadmin),
    )

    assert response.status_code == 200
    assert response.json()["staff"]["role"]["name"] == "Super Admin"


def test_non_super_admin_cannot_modify_an_existing_super_admins_role(
    test_client, db_session, superadmin_role
):
    edit_roles = _make_permission(db_session, Permission.EDIT_STAFF_ROLES)
    manager_role = _make_role(db_session, "RoleManager", allowed=[edit_roles])

    acting_staff = _make_staff(db_session, manager_role, "manager@example.com")
    target_super_admin = _make_staff(db_session, superadmin_role, "other.admin@example.com")

    response = test_client.patch(
        f"/api/staff/{target_super_admin.id}/roles-permissions",
        json={"role": "Viewer"},
        headers=_headers(acting_staff),
    )

    assert response.status_code == 403
    assert "modify another super admin" in response.json()["detail"].lower()


def test_staff_not_found_returns_404(test_client, db_session):
    edit_roles = _make_permission(db_session, Permission.EDIT_STAFF_ROLES)
    role = _make_role(db_session, "RoleManager", allowed=[edit_roles])
    staff = _make_staff(db_session, role, "manager@example.com")

    response = test_client.patch(
        f"/api/staff/{uuid4()}/roles-permissions",
        json={"role": "Viewer"},
        headers=_headers(staff),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /staff/{staff_id} (update_staff_details) used to have no permission
# gate at all — any authenticated ERP user could edit any other staff
# member's name/email.
# ---------------------------------------------------------------------------


def test_update_staff_details_denied_without_permission(test_client, db_session):
    role = _make_role(db_session, "NoPerms")
    acting_staff = _make_staff(db_session, role, "acting@example.com")
    target_staff = _make_staff(db_session, role, "target@example.com")

    response = test_client.patch(
        f"/api/staff/{target_staff.id}",
        json={
            "first_name": "Changed",
            "last_name": "Name",
            "email": "changed@example.com",
        },
        headers=_headers(acting_staff),
    )

    assert response.status_code == 403


def test_update_staff_details_allowed_with_permission(test_client, db_session):
    edit_roles = _make_permission(db_session, Permission.EDIT_STAFF_ROLES)
    role = _make_role(db_session, "RoleManager", allowed=[edit_roles])
    acting_staff = _make_staff(db_session, role, "acting@example.com")
    target_staff = _make_staff(db_session, role, "target@example.com")

    response = test_client.patch(
        f"/api/staff/{target_staff.id}",
        json={
            "first_name": "Changed",
            "last_name": "Name",
            "email": "changed@example.com",
        },
        headers=_headers(acting_staff),
    )

    assert response.status_code == 200
    assert response.json()["staff"]["email"] == "changed@example.com"
