import time

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.hash import Hasher
from app.models.erp_recovery_code import ERPRecoveryCode
from app.models.erp_user import ERPUser
from app.models.role import SUPER_ADMIN, Role
from app.services.auth import AuthService
from app.utils.settings import settings

BASE = "/api/auth/erp"
PASSWORD = "@Password123"


@pytest.fixture(autouse=True)
def mfa_key(monkeypatch):
    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())


def _make_staff(db_session, email="mfa@example.com", role_name="Support") -> ERPUser:
    role = Role(name=role_name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    staff = ERPUser(
        first_name="Mfa",
        last_name="User",
        email=email,
        hashed_password=Hasher.get_password_hash(PASSWORD),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


@pytest.fixture
def staff(db_session) -> ERPUser:
    return _make_staff(db_session)


def _headers(user: ERPUser) -> dict:
    token = AuthService.create_access_token(
        data={"sub": str(user.id), "account_type": "erp"}
    )
    return {"Authorization": f"Bearer {token}"}


def _code(secret: str, offset_steps: int = 0) -> str:
    """A valid code for a step relative to now (each step is 30s). The enable
    step is consumed, so later calls must use a newer one to avoid replay."""
    return pyotp.TOTP(secret).at(int(time.time()) + 30 * offset_steps)


def _enroll(test_client, user: ERPUser) -> tuple[str, list[str]]:
    """Run setup + enable. Returns (secret, recovery_codes); the enable code
    uses the current step."""
    secret = test_client.post(f"{BASE}/2fa/setup", headers=_headers(user)).json()[
        "secret"
    ]
    res = test_client.post(
        f"{BASE}/2fa/enable", headers=_headers(user), json={"code": _code(secret)}
    )
    assert res.status_code == 200
    return secret, res.json()["recovery_codes"]


def _login(test_client, user: ERPUser):
    return test_client.post(
        f"{BASE}/login", json={"email": user.email, "password": PASSWORD}
    )


def test_login_without_2fa_is_unchanged(test_client, staff):
    res = _login(test_client, staff)
    assert res.status_code == 200
    assert res.json()["access_token"]
    assert res.json()["mfa_required"] is False


def test_setup_does_not_enforce_until_enabled(test_client, db_session, staff):
    res = test_client.post(f"{BASE}/2fa/setup", headers=_headers(staff))
    assert res.status_code == 200
    assert res.json()["otpauth_uri"].startswith("otpauth://totp/")

    db_session.refresh(staff)
    assert staff.totp_secret and staff.totp_secret != res.json()["secret"]  # encrypted
    assert _login(test_client, staff).json()["access_token"]


def test_enable_rejects_wrong_code(test_client, staff):
    test_client.post(f"{BASE}/2fa/setup", headers=_headers(staff))
    res = test_client.post(
        f"{BASE}/2fa/enable", headers=_headers(staff), json={"code": "000000"}
    )
    assert res.status_code == 400


def test_full_login_flow_with_totp(test_client, staff):
    secret, recovery_codes = _enroll(test_client, staff)
    assert len(recovery_codes) == 10

    res = _login(test_client, staff)
    assert res.status_code == 200
    body = res.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert body["access_token"] is None
    assert "refresh_token" not in res.cookies

    res = test_client.post(
        f"{BASE}/login/2fa",
        json={"mfa_token": body["mfa_token"], "code": _code(secret, 1)},
    )
    assert res.status_code == 200
    assert res.json()["access_token"]
    assert "refresh_token" in res.cookies


def test_replayed_code_is_rejected(test_client, staff):
    secret, _ = _enroll(test_client, staff)
    mfa_token = _login(test_client, staff).json()["mfa_token"]

    # The enable step's code is already spent.
    res = test_client.post(
        f"{BASE}/login/2fa", json={"mfa_token": mfa_token, "code": _code(secret)}
    )
    assert res.status_code == 401


def test_wrong_code_then_lockout(test_client, staff):
    secret, _ = _enroll(test_client, staff)
    mfa_token = _login(test_client, staff).json()["mfa_token"]

    for _ in range(5):
        res = test_client.post(
            f"{BASE}/login/2fa", json={"mfa_token": mfa_token, "code": "000000"}
        )
        assert res.status_code == 401

    # Locked now, even with a correct code.
    res = test_client.post(
        f"{BASE}/login/2fa", json={"mfa_token": mfa_token, "code": _code(secret, 1)}
    )
    assert res.status_code == 429


def test_recovery_code_is_single_use(test_client, staff):
    _, recovery_codes = _enroll(test_client, staff)

    mfa_token = _login(test_client, staff).json()["mfa_token"]
    res = test_client.post(
        f"{BASE}/login/2fa", json={"mfa_token": mfa_token, "code": recovery_codes[0]}
    )
    assert res.status_code == 200

    mfa_token = _login(test_client, staff).json()["mfa_token"]
    res = test_client.post(
        f"{BASE}/login/2fa", json={"mfa_token": mfa_token, "code": recovery_codes[0]}
    )
    assert res.status_code == 401


def test_mfa_token_is_not_a_session(test_client, staff):
    _enroll(test_client, staff)
    mfa_token = _login(test_client, staff).json()["mfa_token"]

    res = test_client.post(
        f"{BASE}/change-password", headers={"Authorization": f"Bearer {mfa_token}"}, json={}
    )
    assert res.status_code == 401

    test_client.cookies.set("refresh_token", mfa_token)
    assert test_client.post(f"{BASE}/refresh").status_code == 401


def test_me_reports_totp_enabled(test_client, staff):
    assert test_client.get("/api/erp/me", headers=_headers(staff)).json()["totp_enabled"] is False
    _enroll(test_client, staff)
    assert test_client.get("/api/erp/me", headers=_headers(staff)).json()["totp_enabled"] is True


def test_refresh_token_is_not_a_session(test_client, staff):
    refresh = AuthService.create_refresh_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    res = test_client.get("/api/erp/me", headers={"Authorization": f"Bearer {refresh}"})
    assert res.status_code == 401


def test_login_2fa_rejects_access_token_as_mfa_token(test_client, staff):
    secret, _ = _enroll(test_client, staff)
    access = AuthService.create_access_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    res = test_client.post(
        f"{BASE}/login/2fa", json={"mfa_token": access, "code": _code(secret, 1)}
    )
    assert res.status_code == 401


def test_disable_requires_password_and_code(test_client, db_session, staff):
    secret, _ = _enroll(test_client, staff)

    bad_password = test_client.post(
        f"{BASE}/2fa/disable",
        headers=_headers(staff),
        json={"password": "wrong", "code": _code(secret, 1)},
    )
    assert bad_password.status_code == 400

    ok = test_client.post(
        f"{BASE}/2fa/disable",
        headers=_headers(staff),
        json={"password": PASSWORD, "code": _code(secret, 1)},
    )
    assert ok.status_code == 200

    db_session.expire_all()
    assert db_session.query(ERPRecoveryCode).count() == 0
    assert _login(test_client, staff).json()["access_token"]


def test_regenerate_recovery_codes_invalidates_old_ones(test_client, staff):
    secret, old_codes = _enroll(test_client, staff)

    res = test_client.post(
        f"{BASE}/2fa/recovery-codes/regenerate",
        headers=_headers(staff),
        json={"code": _code(secret, 1)},
    )
    assert res.status_code == 200
    new_codes = res.json()["recovery_codes"]
    assert set(new_codes).isdisjoint(old_codes)

    mfa_token = _login(test_client, staff).json()["mfa_token"]
    res = test_client.post(
        f"{BASE}/login/2fa", json={"mfa_token": mfa_token, "code": old_codes[0]}
    )
    assert res.status_code == 401


def test_super_admin_can_reset_2fa(test_client, db_session, staff):
    _enroll(test_client, staff)
    admin = _make_staff(db_session, email="admin@example.com", role_name=SUPER_ADMIN)

    res = test_client.post(f"/api/staff/{staff.id}/2fa/reset", headers=_headers(admin))
    assert res.status_code == 200

    db_session.expire_all()
    assert db_session.get(ERPUser, staff.id).totp_enabled is False
    assert _login(test_client, staff).json()["access_token"]


def test_non_admin_cannot_reset_2fa(test_client, db_session, staff):
    other = _make_staff(db_session, email="other@example.com", role_name="Other")
    res = test_client.post(f"/api/staff/{staff.id}/2fa/reset", headers=_headers(other))
    assert res.status_code == 403
