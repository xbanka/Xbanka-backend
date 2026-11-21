import hmac
import logging

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.role import SUPER_ADMIN
from app.services.auth import AuthService
from app.services.erp_user import ERPService
from app.utils.schema import CurrentUser
from app.utils.settings import settings

logger = logging.getLogger(__name__)

DENIED_DETAIL = "You are not allowed to access this resource"


def _names(items) -> list[str]:
    """Permission enums and plain strings both end up as readable names."""
    return [str(getattr(item, "value", item)) for item in items]


def _deny(current_user: CurrentUser, reason: str, required: list[str]) -> HTTPException:
    """Log why a signed-in caller was refused (the request line carries the path)
    and build the 403."""
    logger.warning(
        "permission denied",
        extra={
            "actor_id": str(current_user.user.id),
            "account_type": current_user.account_type,
            "reason": reason,
            "required": required,
        },
    )
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=DENIED_DETAIL)


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    """Guard for calls from the core backend, which has no staff login: it
    proves itself with the shared `x-internal-key` (the same value the ERP
    sends to the core). Compared in constant time; an unset key closes the
    route instead of matching an empty header."""
    expected = settings.INTERNAL_KEY or ""
    if not expected:
        reason = "not_configured"
    elif not x_internal_key:
        reason = "missing"
    elif not hmac.compare_digest(x_internal_key.encode(), expected.encode()):
        reason = "mismatch"
    else:
        return
    # The reason is enough to tell a misconfigured environment from an attack;
    # the header value is never logged.
    logger.warning("internal key rejected", extra={"reason": reason})
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=DENIED_DETAIL)


def require_account_type(*allowed_types: str):
    def decorator(
        current_user: CurrentUser = Depends(AuthService.get_current_user),
    ):
        if current_user.account_type not in allowed_types:
            raise _deny(current_user, "wrong_account_type", list(allowed_types))
        return current_user

    return decorator

def require_permissions(*permissions: str):
    def decorator(
        current_user: CurrentUser = Depends(AuthService.get_current_user),
        db: Session = Depends(get_db),
    ):
        if current_user.account_type != "erp":
            raise _deny(current_user, "wrong_account_type", ["erp"])
        if current_user.user.role.name != SUPER_ADMIN:
            staff_permissions = ERPService.get_staff_permissions(
                db, current_user.user.id
            )
            if not any(p in staff_permissions for p in permissions):
                raise _deny(current_user, "missing_permission", _names(permissions))
        return current_user

    return decorator

def require_super_admin(current_user: CurrentUser = Depends(AuthService.get_current_user)):
    if current_user.account_type != "erp" or current_user.user.role.name != SUPER_ADMIN:
        raise _deny(current_user, "not_super_admin", [SUPER_ADMIN])
    return current_user
