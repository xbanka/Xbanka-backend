import hmac

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.role import SUPER_ADMIN
from app.services.auth import AuthService
from app.services.erp_user import ERPService
from app.utils.schema import CurrentUser
from app.utils.settings import settings


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    """Guard for calls from the core backend, which has no staff login: it
    proves itself with the shared `x-internal-key` (the same value the ERP
    sends to the core). Compared in constant time; an unset key closes the
    route instead of matching an empty header."""
    expected = settings.INTERNAL_KEY or ""
    if (
        not expected
        or not x_internal_key
        or not hmac.compare_digest(x_internal_key.encode(), expected.encode())
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this resource",
        )


def require_account_type(*allowed_types: str):
    def decorator(
        current_user: CurrentUser = Depends(AuthService.get_current_user),
    ):
        if current_user.account_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource",
            )
        return current_user

    return decorator

def require_permissions(*permissions: str):
    def decorator(
        current_user: CurrentUser = Depends(AuthService.get_current_user),
        db: Session = Depends(get_db),
    ):
        if current_user.account_type != "erp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource",
            )
        if current_user.user.role.name != SUPER_ADMIN:
            staff_permissions = ERPService.get_staff_permissions(
                db, current_user.user.id
            )
            if not any(p in staff_permissions for p in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not allowed to access this resource",
                )
        return current_user

    return decorator

def require_super_admin(current_user: CurrentUser = Depends(AuthService.get_current_user)):
    if current_user.account_type != "erp" or current_user.user.role.name != SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this resource",
        )
    return current_user
