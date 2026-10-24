"""TOTP two-factor auth for ERP staff.

Secrets are Fernet-encrypted at rest (MFA_ENCRYPTION_KEY); recovery codes are
bcrypt-hashed and single-use. Failed second-factor attempts are counted on the
user row and lock further attempts for a while, since there is no rate limiter
in front of the API.
"""

import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import NotificationReferenceTypeEnum
from app.core.hash import Hasher
from app.models.erp_recovery_code import ERPRecoveryCode
from app.models.erp_user import ERPUser
from app.services.erp_user import ERPService
from app.utils.settings import settings

logger = logging.getLogger(__name__)

TOTP_INTERVAL = 30
# Accept one step either side of "now" to tolerate clock drift.
TOTP_WINDOW = 1
MAX_FAILED_ATTEMPTS = 5
LOCKOUT = timedelta(minutes=15)
RECOVERY_CODE_COUNT = 10
# Same ambiguity-free alphabet as staff codes.
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _fernet() -> Fernet:
    if not settings.MFA_ENCRYPTION_KEY:
        logger.error("MFA_ENCRYPTION_KEY is not configured")
        raise HTTPException(
            status_code=500, detail="Two-factor authentication is not configured."
        )
    return Fernet(settings.MFA_ENCRYPTION_KEY.encode())


def _decrypt_secret(user: ERPUser) -> str:
    try:
        return _fernet().decrypt(user.totp_secret.encode()).decode()
    except InvalidToken as e:
        logger.exception("could not decrypt TOTP secret", extra={"user_id": str(user.id)})
        raise HTTPException(
            status_code=500, detail="Two-factor authentication is misconfigured."
        ) from e


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _new_recovery_code() -> str:
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(10))
    return f"{raw[:5]}-{raw[5:]}"


def _notify(db: Session, user: ERPUser, message: str) -> None:
    ERPService.new_notification(
        db,
        recipients=[user],
        message=message,
        reference_type=NotificationReferenceTypeEnum.STAFF_ACCOUNT,
        reference_id=user.id,
    )


class MFAService:
    @staticmethod
    def begin_setup(db: Session, user: ERPUser) -> dict:
        """Generate (or regenerate) a pending secret. It is not enforced at
        login until enable() confirms a code from the authenticator app."""
        if user.totp_enabled:
            raise HTTPException(
                status_code=400, detail="Two-factor authentication is already enabled."
            )

        secret = pyotp.random_base32()
        user.totp_secret = _fernet().encrypt(secret.encode()).decode()
        user.totp_last_used_step = None
        db.commit()

        uri = pyotp.TOTP(secret, interval=TOTP_INTERVAL).provisioning_uri(
            name=user.email, issuer_name=settings.MFA_ISSUER
        )
        return {"secret": secret, "otpauth_uri": uri}

    @staticmethod
    def enable(db: Session, user: ERPUser, code: str) -> list[str]:
        if user.totp_enabled:
            raise HTTPException(
                status_code=400, detail="Two-factor authentication is already enabled."
            )
        if not user.totp_secret:
            raise HTTPException(
                status_code=400, detail="Start 2FA setup before confirming a code."
            )

        if not MFAService._verify_totp(db, user, code):
            raise HTTPException(status_code=400, detail="Invalid verification code.")

        user.totp_enabled = True
        user.mfa_failed_attempts = 0
        user.mfa_locked_until = None
        codes = MFAService._replace_recovery_codes(db, user)
        _notify(db, user, "Two-factor authentication was enabled on your account.")
        logger.info("2fa enabled", extra={"user_id": str(user.id)})
        return codes

    @staticmethod
    def disable(db: Session, user: ERPUser, password: str, code: str) -> None:
        if not user.totp_enabled:
            raise HTTPException(
                status_code=400, detail="Two-factor authentication is not enabled."
            )
        # 400 rather than 401: the caller is authenticated, and a 401 would read
        # to the frontend as an expired session.
        if not user.hashed_password or not Hasher.verify_password(
            password, user.hashed_password
        ):
            raise HTTPException(status_code=400, detail="Password is incorrect.")

        MFAService.verify_second_factor(db, user, code)
        MFAService._clear(db, user)
        _notify(
            db,
            user,
            "Two-factor authentication was disabled on your account. "
            "If this wasn't you, reset your password immediately.",
        )
        logger.warning("2fa disabled", extra={"user_id": str(user.id)})

    @staticmethod
    def admin_reset(db: Session, user: ERPUser, actor: ERPUser) -> None:
        MFAService._clear(db, user)
        _notify(
            db,
            user,
            "Two-factor authentication was reset on your account by an administrator. "
            "Set it up again from your security settings.",
        )
        logger.warning(
            "2fa reset by admin",
            extra={"user_id": str(user.id), "actor_id": str(actor.id)},
        )

    @staticmethod
    def regenerate_recovery_codes(db: Session, user: ERPUser, code: str) -> list[str]:
        if not user.totp_enabled:
            raise HTTPException(
                status_code=400, detail="Two-factor authentication is not enabled."
            )
        MFAService.verify_second_factor(db, user, code)
        return MFAService._replace_recovery_codes(db, user)

    @staticmethod
    def verify_second_factor(db: Session, user: ERPUser, code: str) -> None:
        """Accept a TOTP code or an unused recovery code, enforcing the
        lockout. Raises 401 on a bad code and 429 while locked."""
        now = datetime.now(timezone.utc)
        if user.mfa_locked_until and _aware(user.mfa_locked_until) > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Try again later.",
            )

        code = (code or "").strip()
        ok = (
            MFAService._verify_totp(db, user, code)
            if code.replace(" ", "").isdigit()
            else MFAService._consume_recovery_code(db, user, code)
        )

        if not ok:
            user.mfa_failed_attempts = (user.mfa_failed_attempts or 0) + 1
            if user.mfa_failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.mfa_locked_until = now + LOCKOUT
                user.mfa_failed_attempts = 0
                logger.warning("2fa locked", extra={"user_id": str(user.id)})
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code."
            )

        user.mfa_failed_attempts = 0
        user.mfa_locked_until = None
        db.commit()

    @staticmethod
    def _verify_totp(db: Session, user: ERPUser, code: str) -> bool:
        code = code.replace(" ", "")
        if not user.totp_secret or len(code) != 6 or not code.isdigit():
            return False

        totp = pyotp.TOTP(_decrypt_secret(user), interval=TOTP_INTERVAL)
        current_step = int(time.time()) // TOTP_INTERVAL
        for step in range(current_step - TOTP_WINDOW, current_step + TOTP_WINDOW + 1):
            if hmac.compare_digest(totp.generate_otp(step), code):
                if user.totp_last_used_step is not None and step <= user.totp_last_used_step:
                    return False  # replay of an already-accepted code
                user.totp_last_used_step = step
                db.commit()
                return True
        return False

    @staticmethod
    def _consume_recovery_code(db: Session, user: ERPUser, code: str) -> bool:
        normalized = code.upper().replace(" ", "")
        for row in user.recovery_codes:
            if row.used_at is None and Hasher.verify_password(normalized, row.code_hash):
                row.used_at = datetime.now(timezone.utc)
                db.commit()
                logger.warning("2fa recovery code used", extra={"user_id": str(user.id)})
                return True
        return False

    @staticmethod
    def _replace_recovery_codes(db: Session, user: ERPUser) -> list[str]:
        for row in list(user.recovery_codes):
            db.delete(row)
        codes = [_new_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
        for code in codes:
            db.add(ERPRecoveryCode(user_id=user.id, code_hash=Hasher.get_password_hash(code)))
        db.commit()
        db.refresh(user)
        return codes

    @staticmethod
    def _clear(db: Session, user: ERPUser) -> None:
        for row in list(user.recovery_codes):
            db.delete(row)
        user.totp_secret = None
        user.totp_enabled = False
        user.totp_last_used_step = None
        user.mfa_failed_attempts = 0
        user.mfa_locked_until = None
        db.commit()
