import pytest
from sqlalchemy import select

from app.models.erp_user import ERPUser
from app.models.role import SUPER_ADMIN, Role

URL = "/api/auth/super-admin/signup"

PAYLOAD = {
    "first_name": "Ada",
    "last_name": "Okafor",
    "email": "ada.okafor@example.com",
    "password": "@Password123",
    "confirm_password": "@Password123",
}


@pytest.fixture
def bootstrap_enabled(monkeypatch):
    # The flag is read into a module constant at import time, so patch that.
    monkeypatch.setattr("app.services.erp_user.ALLOW_SUPER_ADMIN_BOOTSTRAP", True)


def _super_admins(db_session):
    return db_session.scalars(
        select(ERPUser).join(Role, Role.id == ERPUser.role_id).where(Role.name == SUPER_ADMIN)
    ).all()


def test_signup_disabled_when_flag_is_off(test_client, superadmin_role, monkeypatch):
    monkeypatch.setattr("app.services.erp_user.ALLOW_SUPER_ADMIN_BOOTSTRAP", False)

    response = test_client.post(URL, json=PAYLOAD)

    assert response.status_code == 403
    assert response.json()["detail"] == "Super Admin creation is disabled."


def test_signup_creates_first_super_admin(
    test_client, db_session, superadmin_role, bootstrap_enabled
):
    response = test_client.post(URL, json=PAYLOAD)

    assert response.status_code == 201
    (created,) = _super_admins(db_session)
    assert created.email == PAYLOAD["email"]
    assert created.verified is True


def test_signup_blocked_once_a_super_admin_exists(
    test_client, db_session, verified_superadmin, bootstrap_enabled
):
    response = test_client.post(URL, json=PAYLOAD)

    assert response.status_code == 409
    assert response.json()["detail"] == "A Super Admin already exists. Signup is closed."
    assert [u.id for u in _super_admins(db_session)] == [verified_superadmin.id]


def test_second_signup_after_first_is_blocked(
    test_client, db_session, superadmin_role, bootstrap_enabled
):
    assert test_client.post(URL, json=PAYLOAD).status_code == 201

    second = test_client.post(URL, json={**PAYLOAD, "email": "other@example.com"})

    assert second.status_code == 409
    assert len(_super_admins(db_session)) == 1


def test_non_super_admin_users_do_not_block_signup(
    test_client, db_session, superadmin_role, bootstrap_enabled
):
    from app.core.hash import Hasher

    admin_role = Role(name="Admin")
    db_session.add(admin_role)
    db_session.commit()
    db_session.add(
        ERPUser(
            first_name="Plain",
            last_name="Admin",
            email="plain.admin@example.com",
            staff_code="ST-AAAAA",
            hashed_password=Hasher.get_password_hash("@Password123"),
            verified=True,
            role_id=admin_role.id,
        )
    )
    db_session.commit()

    response = test_client.post(URL, json=PAYLOAD)

    assert response.status_code == 201
