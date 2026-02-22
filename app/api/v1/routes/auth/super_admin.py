from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.erp.user import RegisterBase, RegisterResponse
from app.services.erp_user import ERPService

super_admin = APIRouter(prefix="/super-admin")


@super_admin.post(
    "/signup", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
def super_admin_signup(login_request: RegisterBase, db: Session = Depends(get_db)):
    super_admin = ERPService.create_superadmin(db, login_request)

    return {
        "message": "Super Admin account created. Welcome to Xbanka ERP",
        "user": super_admin,
    }
