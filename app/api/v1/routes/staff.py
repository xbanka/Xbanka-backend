from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.email import send_invite_email
from app.db.database import get_db
from app.schemas.erp.user import InviteStaffRequest
from app.services.erp_user import ERPService
from app.utils.settings import settings
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser
from sqlalchemy.orm import Session

staff = APIRouter(prefix='/staff')

ERP_FRONTEND_URL = settings.ERP_FRONTEND_URL

@staff.post("/invite", status_code=status.HTTP_200_OK)
async def invite_staff(
    request: InviteStaffRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db), 
    current_user: CurrentUser = Depends(require_roles("erp", "super"))
):
    staff = ERPService.invite_staff(
        db,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        role=request.role,
        selected_permissions=request.permissions
    )

    url = f"{ERP_FRONTEND_URL}/signup?email={staff.email}"

    await send_invite_email(
        recipient=staff.email,
        first_name=str(staff.first_name),
        last_name=str(staff.last_name),
        signup_url=url,
        background_tasks=background_tasks,
    )

    return {
        "message": f"Staff member {staff.email} invited successfully.",
        "staff": staff,
    }


@staff.get("/permissions", status_code=status.HTTP_200_OK)
def get_role_permissions(role: str = Query(...), db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_roles("erp", "super"))):
    permissions = ERPService.get_role_permissions(db, role)
    return {
        "permissions": permissions
    }