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

def require_permission(permission: str):
    def decorator(current_user: CurrentUser = Depends(AuthService.get_current_user)):
        if permission not in current_user.user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource",
            )
        return current_user

    return decorator
