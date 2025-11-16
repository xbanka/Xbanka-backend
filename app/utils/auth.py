from fastapi import Depends, HTTPException, status
from app.services.auth import AuthService

def require_role(*allowed_roles: str):
    def decorator(user = Depends(AuthService.get_current_user)):
        if user.assigned_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource"
            )
        return user
    return decorator
