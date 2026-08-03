from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.enums import PayoutMethodEnum, PayoutStatusEnum
from app.db.database import get_db
from app.schemas.erp.notifications import (
    NotificationReadResponse,
    NotificationsResponse,
)
from app.schemas.erp.payout import ERPPaginatedPayoutResponse, ERPPayoutResponse, ERPPayoutDetailResponse, ERPProcessPayoutResponse
from app.schemas.erp.user import ERPMeResponse
from app.schemas.payout import ProcessPayoutRequest
from app.services.erp_user import ERPService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

erp = APIRouter(prefix="/erp", tags=["ERP"])


@erp.get("/me", status_code=status.HTTP_200_OK, response_model=ERPMeResponse)
def get_current_erp(current_user: CurrentUser = Depends(require_roles("erp"))):
    return current_user.user


@erp.get("/notifications", response_model=List[NotificationsResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    return ERPService.get_notifications(db)


@erp.patch(
    "/notifications/{notification_id}/mark-as-read",
    response_model=NotificationReadResponse,
)
def mark_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    notif = ERPService.mark_notification_as_read(db, notification_id)
    return notif


@erp.get(
    "/payouts",
    status_code=status.HTTP_200_OK,
    response_model=ERPPaginatedPayoutResponse,
)
def get_all_payouts(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp")),
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
    current_user: CurrentUser = Depends(require_roles("erp")),
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
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    payout = ERPService.process_payout(db, payout_id, process_request)

    ERPService.new_notification(
        db,
        user=current_user.user,
        message="Payout has been processed successfully",
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
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    payout = ERPService.reject_payout(db, payout_id)

    ERPService.new_notification(
        db,
        user=current_user.user,
        message="Payout has been rejected",
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
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    payout = ERPService.upload_attachment(
        db=db, payout_id=payout_id, attachment=attachment
    )
    return {"message": "Attachment uploaded successfully", "payout": payout}
