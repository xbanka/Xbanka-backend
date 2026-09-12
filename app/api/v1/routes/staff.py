from typing import Union
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.email import send_invite_email
from app.core.enums import Permission
from app.db.database import get_db
from app.models.role_change_log import RoleChangeLog
from app.schemas.erp.audit import RoleChangeDetail, RoleChangeProposedResponse
from app.schemas.erp.user import (
    AllStaffResponse,
    InviteStaffRequest,
    StaffListItem,
    UpdatePermissionsRequest,
    UpdatePermissionsResponse,
    UpdateStaffRequest,
)
from app.services.erp_user import ERPService
from app.utils.auth import require_account_type, require_super_admin, require_permissions
from app.utils.schema import CurrentUser
from app.utils.settings import settings

staff = APIRouter(prefix="/staff", tags=["Staff"])

MANAGE_CUSTOMERS = Permission.MANAGE_CUSTOMERS
ADD_STAFF = Permission.ADD_STAFF
VIEW_STAFF_LIST = Permission.VIEW_STAFF_LIST
EDIT_STAFF_ROLES = Permission.EDIT_STAFF_ROLES
EDIT_STAFF_PERMISSIONS = Permission.EDIT_STAFF_PERMISSIONS


ERP_FRONTEND_URL = settings.ERP_FRONTEND_URL


@staff.get("/all", response_model=AllStaffResponse, status_code=status.HTTP_200_OK)
def get_all_staff(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(VIEW_STAFF_LIST))
):
    staff_members = ERPService.get_all_staff(db)
    pending = ERPService.get_pending_role_changes(
        db, [member.id for member in staff_members]
    )

    items = []
    for member in staff_members:
        item = StaffListItem.model_validate(member)
        role_change = pending.get(member.id)
        if role_change is not None:
            item.role_change = RoleChangeDetail(
                previous_role=role_change.previous_role,
                new_role=role_change.new_role,
            )
        items.append(item)

    return {"staff": items, "count": len(items)}


@staff.post("/invite", status_code=status.HTTP_200_OK)
async def invite_staff(
    request: InviteStaffRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(ADD_STAFF))
):
    staff = ERPService.invite_staff(
        db,
        email=request.email,
        role_name=request.role,
        selected_permissions=request.permissions,
    )

    url = f"{ERP_FRONTEND_URL}/signup?email={staff.email}"

    await send_invite_email(
        recipient=staff.email,
        signup_url=url,
        background_tasks=background_tasks,
    )

    return {
        "message": f"Staff member {staff.email} invited successfully.",
        "staff": staff,
    }


@staff.get("/permissions", status_code=status.HTTP_200_OK)
def get_role_permissions(
    role: str = Query(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    default = ERPService.get_role_permissions(db, role)
    # Roles no longer forbid permissions; "forbidden" stays for frontend compatibility.
    return {"default": default, "forbidden": []}


@staff.get("/{staff_id}/permissions", status_code=status.HTTP_200_OK)
def get_staff_permissions(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    permissions = ERPService.get_staff_permissions(db, staff_id)
    return {"permissions": permissions}


@staff.delete("/{staff_id}", status_code=status.HTTP_200_OK)
def remove_staff_member(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_super_admin)
):
    ERPService.remove_staff_member(db, staff_id)
    return {"message": "Staff member removed successfully."}


@staff.patch("/{staff_id}", status_code=status.HTTP_200_OK)
def update_staff_details(
    staff_id: UUID,
    update_request: UpdateStaffRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(EDIT_STAFF_ROLES)),
):
    staff = ERPService.update_staff_details(db, staff_id, update_request)
    return {"message": "Staff member details updated successfully.", "staff": staff}


@staff.patch(
    "/{staff_id}/roles-permissions",
    response_model=Union[UpdatePermissionsResponse, RoleChangeProposedResponse],
    status_code=status.HTTP_200_OK,
)
def update_staff_roles_permissions(
    staff_id: UUID,
    request: UpdatePermissionsRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(EDIT_STAFF_PERMISSIONS, EDIT_STAFF_ROLES)),
):
    result = ERPService.update_staff_roles_permissions(
        db, staff_id, request.role, request.permissions, request.reason, current_user.user
    )
    if isinstance(result, RoleChangeLog):
        return {
            "message": "Role change proposed. The staff member must confirm it before it takes effect.",
            "role_change_id": result.id,
            "status": result.status,
        }
    return {
        "message": "Staff member's role and permissions updated successfully.",
        "staff": result,
    }
