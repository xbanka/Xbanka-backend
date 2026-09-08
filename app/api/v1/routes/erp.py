from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from app.core.enums import (
    NotificationReferenceTypeEnum,
    NotificationStatusEnum,
    PayoutMethodEnum,
    PayoutStatusEnum,
    Permission as PermissionEnum,
)
from app.db.database import get_db
from app.schemas.erp.notifications import (
    NotificationCountsResponse,
    NotificationReadResponse,
    NotificationsResponse,
)
from app.schemas.erp.audit import PendingRoleChangeSummary
from app.schemas.erp.payout import ERPPaginatedPayoutResponse, ERPPayoutResponse, ERPPayoutDetailResponse, ERPProcessPayoutResponse
from app.schemas.erp.user import ERPMeResponse
from app.schemas.payout import ProcessPayoutRequest
from app.services.auth import AuthService
from app.services.erp_user import ERPService
from app.services.websocket_manager import notification_manager
from app.utils.auth import require_account_type, require_permissions
from app.utils.schema import CurrentUser

erp = APIRouter(prefix="/erp", tags=["ERP"])

VIEW_AFFILIATE_PAYOUTS = PermissionEnum.VIEW_AFFILIATE_PAYOUTS
APPROVE_AFFILIATE_PAYOUTS = PermissionEnum.APPROVE_AFFILIATE_PAYOUTS


@erp.get("/me", status_code=status.HTTP_200_OK, response_model=ERPMeResponse)
def get_current_erp(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_account_type("erp", allow_pending_role_change=True)
    ),
):
    pending = ERPService.get_pending_role_change(db, current_user.user.id)
    me = ERPMeResponse.model_validate(current_user.user)
    if pending is not None:
        me.pending_role_change = PendingRoleChangeSummary(
            id=pending.id,
            new_role=pending.new_role,
            reason=pending.reason,
            requested_by=f"{pending.requested_by.first_name} {pending.requested_by.last_name}",
            created_at=pending.created_at,
        )
    return me


@erp.get("/notifications", response_model=List[NotificationsResponse])
def get_notifications(
    status: Optional[NotificationStatusEnum] = Query(None),
    reference_type: Optional[NotificationReferenceTypeEnum] = Query(None),
    is_read: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    return ERPService.get_notifications(
        db,
        current_user.user.id,
        status=status,
        reference_type=reference_type,
        is_read=is_read,
    )


@erp.get("/notifications/counts", response_model=NotificationCountsResponse)
def get_notification_counts(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    return ERPService.get_notification_counts(db, current_user.user.id)


@erp.websocket("/notifications/ws")
async def notifications_websocket(
    websocket: WebSocket,
    current_user: CurrentUser = Depends(AuthService.get_current_user_ws),
):
    user_id = str(current_user.user.id)
    await notification_manager.connect(user_id, websocket)
    try:
        while True:
            # nothing expected from the client; just keep the connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id, websocket)


@erp.patch(
    "/notifications/{notification_id}/mark-as-read",
    response_model=NotificationReadResponse,
)
def mark_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    notif = ERPService.mark_notification_as_read(
        db, notification_id, current_user.user.id
    )
    return notif


@erp.get(
    "/payouts",
    status_code=status.HTTP_200_OK,
    response_model=ERPPaginatedPayoutResponse,
)
def get_all_payouts(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(VIEW_AFFILIATE_PAYOUTS)),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[PayoutStatusEnum] = Query(None, description="Payout Status"),
):
    return ERPService.get_all_payouts(db, page, limit, status)


@erp.get(
    "/payouts/{payout_id}",
    status_code=status.HTTP_200_OK,
    response_model=ERPPayoutDetailResponse,
)
def get_payout_details(
    payout_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(VIEW_AFFILIATE_PAYOUTS)),
):
    return ERPService.get_payout_details(db, payout_id)


@erp.post(
    "/payouts/{payout_id}/process",
    status_code=status.HTTP_200_OK,
    response_model=ERPPayoutResponse,
)
def process_payout(
    payout_id: UUID,
    process_request: ProcessPayoutRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permissions(APPROVE_AFFILIATE_PAYOUTS)),
):
    payout = ERPService.process_payout(db, payout_id, process_request)

    ERPService.notify_permission_holders(
        db,
        PermissionEnum.VIEW_AFFILIATE_PAYOUTS,
        exclude_user_id=current_user.user.id,
        message="Payout has been processed successfully",
        reference_type=NotificationReferenceTypeEnum.PAYOUT,
        amount=payout.amount,
        method=PayoutMethodEnum.bank_transfer,
        affiliate_id=payout.affiliate_id,
        reference_id=payout.id
    )

    return payout


@erp.post(
    "/payouts/{payout_id}/reject",
    status_code=status.HTTP_200_OK,
    response_model=ERPPayoutResponse,
)
def reject_payout(
    payout_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    payout = ERPService.reject_payout(db, payout_id)

    ERPService.notify_permission_holders(
        db,
        PermissionEnum.VIEW_AFFILIATE_PAYOUTS,
        exclude_user_id=current_user.user.id,
        message="Payout has been rejected",
        reference_type=NotificationReferenceTypeEnum.PAYOUT,
        amount=payout.amount,
        method=PayoutMethodEnum.bank_transfer,
        affiliate_id=payout.affiliate_id,
        reference_id=payout.id
    )

    return payout


@erp.post(
    "/payouts/{payout_id}/attachment",
    status_code=status.HTTP_200_OK,
    response_model=ERPProcessPayoutResponse,
)
def upload_payout_attachment(
    payout_id: UUID,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    payout = ERPService.upload_attachment(
        db=db, payout_id=payout_id, attachment=attachment
    )
    return {"message": "Attachment uploaded successfully", "payout": payout}
