from fastapi import Depends, HTTPException, status
from app.services.auth import AuthService
from app.utils.schema import CurrentUser

        
def require_roles(*allowed_roles: str):
    def decorator(current_user: CurrentUser = Depends(AuthService.get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource"
            )
        return current_user
    return decorator