from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.login_log import LoginLog
from app.models.role import Role


def _make_role(db_session, name="Viewer"):
    role = Role(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


def _make_staff(db_session, role, email="staff@example.com", password="@Password123"):
    staff = ERPUser(
        first_name="Test",
        last_name="Staff",
        email=email,
        hashed_password=Hasher.get_password_hash(password),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def test_successful_login_is_logged(test_client, db_session):
    role = _make_role(db_session)
    staff = _make_staff(db_session, role)

    response = test_client.post(
        "/api/auth/erp/login",
        json={"email": staff.email, "password": "@Password123"},
    )

    assert response.status_code == 200

    logs = db_session.query(LoginLog).filter(LoginLog.attempted_email == staff.email).all()
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].user_id == staff.id
    assert logs[0].ip_address is not None


def test_failed_login_with_wrong_password_is_logged_against_known_user(test_client, db_session):
    role = _make_role(db_session)
    staff = _make_staff(db_session, role)

    response = test_client.post(
        "/api/auth/erp/login",
        json={"email": staff.email, "password": "wrong-password"},
    )

    assert response.status_code == 401

    logs = db_session.query(LoginLog).filter(LoginLog.attempted_email == staff.email).all()
    assert len(logs) == 1
    assert logs[0].status == "FAILED"
    assert logs[0].user_id == staff.id
    assert logs[0].failure_reason


def test_failed_login_with_unknown_email_is_logged_without_a_user(test_client, db_session):
    response = test_client.post(
        "/api/auth/erp/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )

    assert response.status_code == 401

    logs = db_session.query(LoginLog).filter(
        LoginLog.attempted_email == "nobody@example.com"
    ).all()
    assert len(logs) == 1
    assert logs[0].status == "FAILED"
    assert logs[0].user_id is None
