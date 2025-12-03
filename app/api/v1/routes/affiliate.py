from typing import Optional
from app.core.enums import PayoutStatusEnum, TransactionStatusEnum, PayoutMethodEnum
from app.schemas.affiliate import (
    AffiliateMeResponse,
    AffiliateCodename, 
    PaginatedTransactionResponse, 
    PaginatedPayoutResponse,
    UpdateBankDetailsRequest,
    UpdateBankDetailsResponse
)
from app.schemas.payout import PayoutSummary, PayoutBase, NewPayoutResponse
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.services.affiliate_payout import PayoutService
from app.services.erp_user import ERPService
from app.db.database import get_db
from app.models import Affiliate

from fastapi import APIRouter, status, Depends, Query, Response
from sqlalchemy.orm import Session


affiliate = APIRouter(prefix="/affiliates", tags=["Affiliates"])

@affiliate.get("/me", status_code=status.HTTP_200_OK, response_model=AffiliateMeResponse)
def get_current_affiliate(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
):
    return current_user

@affiliate.post(
    "/codename", status_code=status.HTTP_201_CREATED, response_model=AffiliateCodename
)
def set_codename(
    codename: str,
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
):
    AffiliateService.set_codename(db, current_user, codename)

    return {"message": "Codename set successfully", "codename": codename}


@affiliate.get("/referral", status_code=status.HTTP_200_OK)
def get_referral_link(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
):
    return AffiliateService.get_referral_code(db, current_user)


@affiliate.get("/all")
def get_all_affiliates(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
):
    return AffiliateService.get_all(db)


@affiliate.get(
    "/commissions",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTransactionResponse,
)
def get_commissions(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[TransactionStatusEnum] = Query(None, description="Commission Status")
):
    return AffiliateService.get_commissions(db, current_user.id, page, limit, status)


@affiliate.get("/commissions/export", response_class=Response)
def export_commissions(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
    status: Optional[TransactionStatusEnum] = Query(None, description="Commission Status")
):
    
    content = AffiliateService.export_commissions(db, current_user.id, status)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=commissions.xlsx"}
    )


@affiliate.post("/payout", status_code=status.HTTP_201_CREATED, response_model=NewPayoutResponse)
def post_payout(
    create_request: PayoutBase, 
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user)
):
    payout = PayoutService.create_new(db, create_request, current_user.id)
    ERPService.new_notification(
        db,
        user=current_user,
        message="Affiliate Payout Request",
        amount=create_request.amount,
        method=PayoutMethodEnum.bank_transfer,
        affiliate_id=payout.affiliate_id
    )

    return {
        "message": "New payout has been created.",
        "payout": payout,
    }


@affiliate.get(
    "/payouts",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedPayoutResponse,
)
def get_payouts(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[PayoutStatusEnum] = Query(None, description="Payout Status")
):
    return AffiliateService.get_payouts(db, current_user.id, page, limit, status)


@affiliate.get("/payouts/export", response_class=Response)
def export_payouts(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
    status: Optional[PayoutStatusEnum] = Query(None, description="Payout Status")
):
    
    content = AffiliateService.export_payouts(db, current_user.id, status)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=payouts.xlsx"}
    )


@affiliate.get("/payouts/summary", status_code=status.HTTP_200_OK, response_model=PayoutSummary)
def get_payouts_summary(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
):
    return AffiliateService.get_payouts_summary(db, current_user.id)


@affiliate.patch("/bank", status_code=status.HTTP_200_OK, response_model=UpdateBankDetailsResponse)
def update_bank_details(
    bank_details: UpdateBankDetailsRequest,
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
):
    AffiliateService.update_bank_details(db, current_user, bank_details)

    return {
        "message": "Bank details updated successfully", 
        "bank_name": bank_details.bank_name,
        "account_number": bank_details.account_number
        }