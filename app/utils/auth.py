from fastapi import Depends, HTTPException, status

from app.services.auth import AuthService
from app.utils.schema import CurrentUser


def require_account_type(*allowed_types: str):
    def decorator(current_user: CurrentUser = Depends(AuthService.get_current_user)):
        if current_user.account_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource",
            )
        return current_user

    return decorator

def require_permissions(*permissions: str):
    def decorator(current_user: CurrentUser = Depends(AuthService.get_current_user)):
        if current_user.account_type != "erp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource",
            )
        if (
            current_user.user.role.name != "Super Admin"
            and not any(p in current_user.user.permissions for p in permissions)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource",
            )
        return current_user

    return decorator

def require_super_admin(current_user: CurrentUser = Depends(AuthService.get_current_user)):
    if current_user.account_type != "erp" or current_user.user.role.name != "Super Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this resource",
        )
    return current_user