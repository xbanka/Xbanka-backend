from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.enums import LoginStatusEnum, Permission as PermissionEnum, RoleChangeStatusEnum
from app.db.database import get_db
from app.schemas.erp.audit import LoginLogResponse, RoleChangeResponse
from app.services.erp_user import ERPService
from app.utils.auth import require_account_type, require_permissions
from app.utils.schema import CurrentUser

audit = APIRouter(prefix="/audit", tags=["Audit"])

VIEW_AUDIT_LOGS = PermissionEnum.VIEW_AUDIT_LOGS


@audit.get("/role-changes", response_model=List[RoleChangeResponse])
def get_role_changes(
    status_filter: Optional[RoleChangeStatusEnum] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(VIEW_AUDIT_LOGS)),
):
    role_changes = ERPService.get_role_changes(
        db, status=status_filter, search=search, page=page, limit=limit
    )
    return [
        {
            "id": rc.id,
            "created_at": rc.created_at,
            "changed_by": f"{rc.requested_by.first_name} {rc.requested_by.last_name}",
            "staff": rc.staff,
            "role_change": {
                "previous_role": rc.previous_role,
                "new_role": rc.new_role,
            },
            "reason": rc.reason,
            "status": rc.status,
        }
        for rc in role_changes
    ]


@audit.post(
    "/role-changes/{role_change_id}/confirm",
    status_code=status.HTTP_200_OK,
)
def confirm_role_change(
    role_change_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    role_change = ERPService.confirm_role_change(db, role_change_id, current_user.user)
    return {"message": "Role change confirmed.", "status": role_change.status}


@audit.get("/logins", response_model=List[LoginLogResponse])
def get_login_logs(
    status_filter: Optional[LoginStatusEnum] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(VIEW_AUDIT_LOGS)),
):
    logs = ERPService.get_login_logs(
        db, status=status_filter, search=search, page=page, limit=limit
    )
    return [
        {
            "id": log.id,
            "created_at": log.created_at,
            "staff": log.user,
            "ip_address": log.ip_address,
            "failure_reason": log.failure_reason,
            "status": log.status,
        }
        for log in logs
    ]
