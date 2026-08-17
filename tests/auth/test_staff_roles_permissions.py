from uuid import uuid4

import pytest

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.models.user_permissions import UserPermissions


@pytest.fixture
def permissions(db_session):
    names = [
        "transactions:view",
        "transactions:create",
        "customers:view",
        "finance:approve_payments",
    ]
    perms = {}
    for name in names:
        perm = Permission(name=name, category=name.split(":")[0])
        db_session.add(perm)
        perms[name] = perm
    db_session.commit()
    for perm in perms.values():
        db_session.refresh(perm)
    return perms


@pytest.fixture
def manager_role(db_session, permissions):
    role = Role(name="Manager")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    db_session.add_all(
        [
            RolePermissions(
                role_id=role.id,
                permission_id=permissions["transactions:view"].id,
                is_allowed=True,
            ),
            RolePermissions(
                role_id=role.id,
                permission_id=permissions["transactions:create"].id,
                is_allowed=True,
            ),
            RolePermissions(
                role_id=role.id,
                permission_id=permissions["finance:approve_payments"].id,
                is_allowed=False,
            ),
        ]
    )
    db_session.commit()
    return role


@pytest.fixture
def viewer_role(db_session, permissions):
    role = Role(name="Viewer")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    db_session.add(
        RolePermissions(
            role_id=role.id,
            permission_id=permissions["customers:view"].id,
            is_allowed=True,
        )
    )
    db_session.commit()
    return role


@pytest.fixture
def target_staff(db_session, viewer_role):
    staff = ERPUser(
        first_name="Target",
        last_name="Staff",
        email="target.staff@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=viewer_role.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _url(staff_id):
    return f"/api/staff/{staff_id}/roles-permissions"


def test_update_role_only_leaves_permission_overrides_untouched(
    super_client, db_session, target_staff, manager_role, permissions
):
    db_session.add(
        UserPermissions(
            user_id=target_staff.id,
            permission_id=permissions["transactions:create"].id,
            is_active=True,
        )
    )
    db_session.commit()

    response = super_client.patch(_url(target_staff.id), json={"role": "Manager"})

    assert response.status_code == 200
    body = response.json()
    assert body["staff"]["role"]["name"] == "Manager"
    assert "hashed_password" not in body["staff"]

    overrides = (
        db_session.query(UserPermissions)
        .filter(UserPermissions.user_id == target_staff.id)
        .all()
    )
    assert len(overrides) == 1
    assert overrides[0].permission_id == permissions["transactions:create"].id


def test_update_permissions_only_leaves_role_untouched(
    super_client, db_session, target_staff, permissions
):
    response = super_client.patch(
        _url(target_staff.id),
        json={"permissions": ["customers:view", "transactions:view"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["staff"]["role"]["name"] == "Viewer"

    overrides = {
        o.permission_id: o.is_active
        for o in db_session.query(UserPermissions).filter(
            UserPermissions.user_id == target_staff.id
        )
    }
    assert overrides.get(permissions["transactions:view"].id) is True


def test_requires_role_or_permissions(super_client, target_staff):
    response = super_client.patch(_url(target_staff.id), json={})
    assert response.status_code == 422


def test_forbidden_permission_rejected(
    super_client, target_staff, manager_role, permissions
):
    response = super_client.patch(
        _url(target_staff.id),
        json={"role": "Manager", "permissions": ["finance:approve_payments"]},
    )
    assert response.status_code == 400
    assert "forbidden" in response.json()["detail"].lower()


def test_forbidden_permission_does_not_wipe_existing_overrides(
    super_client, db_session, target_staff, manager_role, permissions
):
    """Regression test: validation must run before existing overrides are deleted."""
    db_session.add(
        UserPermissions(
            user_id=target_staff.id,
            permission_id=permissions["transactions:create"].id,
            is_active=True,
        )
    )
    db_session.commit()

    response = super_client.patch(
        _url(target_staff.id),
        json={"role": "Manager", "permissions": ["finance:approve_payments"]},
    )
    assert response.status_code == 400

    overrides = (
        db_session.query(UserPermissions)
        .filter(UserPermissions.user_id == target_staff.id)
        .all()
    )
    assert len(overrides) == 1
    assert overrides[0].permission_id == permissions["transactions:create"].id


def test_unknown_permission_rejected(super_client, target_staff):
    response = super_client.patch(
        _url(target_staff.id),
        json={"permissions": ["not:a-real-permission"]},
    )
    assert response.status_code == 400
    assert "unknown permission" in response.json()["detail"].lower()


def test_staff_not_found(super_client):
    response = super_client.patch(_url(uuid4()), json={"role": "Manager"})
    assert response.status_code == 404


def test_role_not_found(super_client, target_staff):
    response = super_client.patch(
        _url(target_staff.id), json={"role": "Nonexistent Role"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# RoleResponse.allowed_permissions (regression: Super Admin used to serialise
# only its own role_permissions rows. In prod those 59 rows all carried
# is_allowed = NULL — RolePermissions.is_allowed defaults Python-side, so rows
# inserted by raw SQL got NULL — and 18 permissions had no row at all, so the
# response silently under-reported. Super Admin must return every permission.)
# ---------------------------------------------------------------------------


def test_super_admin_sees_every_permission_despite_null_and_missing_rows(
    db_session, permissions
):
    from app.schemas.erp.user import RoleResponse

    role = Role(name="Super Admin")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    # exactly the prod shape: a partial set of rows, every one is_allowed = NULL
    db_session.add(
        RolePermissions(
            role_id=role.id,
            permission_id=permissions["transactions:view"].id,
            is_allowed=None,
        )
    )
    db_session.commit()
    db_session.refresh(role)

    allowed = RoleResponse.model_validate(role).allowed_permissions

    assert sorted(allowed) == sorted(permissions)
    assert "finance:approve_payments" in allowed  # never had a row


def test_non_super_admin_still_honours_is_allowed(db_session, manager_role):
    from app.schemas.erp.user import RoleResponse

    allowed = RoleResponse.model_validate(manager_role).allowed_permissions

    assert "transactions:view" in allowed
    assert "finance:approve_payments" not in allowed
