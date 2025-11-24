from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.core.enums import PayoutMethodEnum, PayoutStatusEnum
from app.schemas.erp.payout import ERPPaginatedPayoutResponse, ERPPayoutResponse
from app.utils.auth import require_role
from app.services.erp_user import ERPService
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.erp.notifications import NotificationReadResponse, NotificationsResponse 
from typing import List, Optional

erp = APIRouter(prefix="/erp", tags=["ERP"])

@erp.get("/")
def get_index(current_user = Depends(require_role("erp"))):
    return {
        "message": "hey"
}

@erp.get("/notifications", response_model=List[NotificationsResponse])
def get_notifications(db: Session = Depends(get_db), current_user = Depends(require_role("erp"))):
    return ERPService.get_notifications(db)


@erp.patch("/notifications/{notification_id}/mark-as-read", response_model=NotificationReadResponse)
def mark_as_read(notification_id: UUID, db: Session = Depends(get_db), current_user = Depends(require_role("erp"))):
    notif = ERPService.mark_notification_as_read(db, notification_id)
    return notif


@erp.get(
    "/payouts",
    status_code=status.HTTP_200_OK,
    response_model=ERPPaginatedPayoutResponse,
)
def get_all_payouts(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("erp")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[PayoutStatusEnum] = Query(None, description="Payout Status")
):
    return ERPService.get_all_payouts(db, page, limit, status)


@erp.get("/payouts/{payout_id}", status_code=status.HTTP_200_OK, response_model=ERPPayoutResponse)
def get_payout_details(
    payout_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("erp")),
):
    return ERPService.get_payout_details(db, payout_id)

@erp.post("/payouts/{payout_id}/process", status_code=status.HTTP_200_OK, response_model=ERPPayoutResponse)
def process_payout(
    payout_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("erp")),
):
    payout = ERPService.process_payout(db, payout_id)

    ERPService.new_notification(
        db,
        user=current_user,
        message="Payout has been processed successfully",
        amount=payout.amount,
        bank_name=current_user.bank,
        method=PayoutMethodEnum.bank_transfer,
    )

    return payout