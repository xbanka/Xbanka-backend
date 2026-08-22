import pytest

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.permission import Permission as PermissionModel
from app.models.role import Role
from app.models.role_permissions import RolePermissions


@pytest.fixture
def add_staff_permission(db_session) -> PermissionModel:
    row = PermissionModel(name="staff:add", category="staff")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def staff_role(db_session, add_staff_permission) -> Role:
    """A role a staff member can be invited into. Needs at least one
    RolePermissions row: get_role_permissions treats a role with none as
    not found."""
    role = Role(name="Support")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    db_session.add(
        RolePermissions(
            role_id=role.id,
            permission_id=add_staff_permission.id,
            is_allowed=True,
        )
    )
    db_session.commit()
    return role


@pytest.fixture
def other_role(db_session, add_staff_permission) -> Role:
    role = Role(name="Compliance")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    db_session.add(
        RolePermissions(
            role_id=role.id,
            permission_id=add_staff_permission.id,
            is_allowed=False,
        )
    )
    db_session.commit()
    return role


def _unverified_staff(db_session, role: Role, email: str) -> ERPUser:
    staff = ERPUser(
        first_name="",
        last_name="",
        email=email,
        role_id=role.id,
        verified=False,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _verified_staff(db_session, role: Role, email: str) -> ERPUser:
    staff = ERPUser(
        first_name="Jane",
        last_name="Doe",
        email=email,
        role_id=role.id,
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


# ---------------------------------------------------------------------------
# POST /staff/invite
# ---------------------------------------------------------------------------


def test_invite_new_staff_creates_pending_user_and_sends_email(
    mocker, super_client, db_session, staff_role
):
    mock_send_email = mocker.patch("app.api.v1.routes.staff.send_invite_email")

    email = "new.staff@example.com"
    response = super_client.post(
        "/api/staff/invite",
        json={"email": email, "role": staff_role.name, "permissions": []},
    )

    assert response.status_code == 200
    mock_send_email.assert_called_once()
    assert mock_send_email.call_args.kwargs["recipient"] == email

    staff = db_session.query(ERPUser).filter_by(email=email).one()
    assert staff.verified is False
    assert staff.role_id == staff_role.id


def test_invite_existing_unverified_staff_resends_invite(
    mocker, super_client, db_session, staff_role, other_role
):
    mock_send_email = mocker.patch("app.api.v1.routes.staff.send_invite_email")

    email = "pending.staff@example.com"
    pending = _unverified_staff(db_session, other_role, email)

    response = super_client.post(
        "/api/staff/invite",
        json={"email": email, "role": staff_role.name, "permissions": []},
    )

    assert response.status_code == 200
    mock_send_email.assert_called_once()
    assert mock_send_email.call_args.kwargs["recipient"] == email

    # same row updated in place, not a duplicate; db_session already holds
    # `pending` in its identity map from the setup insert above, so it needs
    # an explicit expire to pick up the API request's commit.
    db_session.expire_all()
    matches = db_session.query(ERPUser).filter_by(email=email).all()
    assert len(matches) == 1
    assert matches[0].id == pending.id
    assert matches[0].role_id == staff_role.id
    assert matches[0].verified is False


def test_invite_verified_staff_rejected(
    mocker, super_client, db_session, staff_role, other_role
):
    mock_send_email = mocker.patch("app.api.v1.routes.staff.send_invite_email")

    email = "already.verified@example.com"
    _verified_staff(db_session, other_role, email)

    response = super_client.post(
        "/api/staff/invite",
        json={"email": email, "role": staff_role.name, "permissions": []},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Staff user with this email already exists"
    mock_send_email.assert_not_called()
