from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.enums import (
    NotificationReferenceTypeEnum,
    PayoutMethodEnum,
    PayoutStatusEnum,
    Permission as PermissionEnum,
)
from app.db.database import get_db
from app.schemas.affiliate import (
    AffiliateCodename,
    AffiliateMeResponse,
    AffiliateTierResponse,
    PaginatedPayoutResponse,
    UpdateBankDetailsRequest,
    UpdateBankDetailsResponse,
)
from app.schemas.payout import NewPayoutResponse, PayoutRequest, PayoutSummary
from app.services.affiliate import AffiliateService
from app.services.affiliate_progress_service import AffiliateProgressService
from app.services.affiliate_payout import PayoutService
from app.services.erp_user import ERPService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

affiliate = APIRouter(prefix="/affiliates", tags=["Affiliates"])


@affiliate.get(
    "/me", status_code=status.HTTP_200_OK, response_model=AffiliateMeResponse
)
def get_current_affiliate(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    affiliate = current_user.user

    progress = AffiliateProgressService.get_affiliate_progress(db, affiliate)

    return AffiliateMeResponse(
        id=affiliate.id,
        first_name=affiliate.first_name,
        last_name=affiliate.last_name,
        email=affiliate.email,
        username=affiliate.username,
        phone_no=affiliate.phone_no,
        ref_code=affiliate.ref_code,
        custom_refcode=affiliate.custom_refcode,
        created_at=affiliate.created_at,
        current_tier=AffiliateTierResponse.model_validate(affiliate.current_tier),
        progress=progress,
        bank_details=affiliate.bank_details,
    )


@affiliate.post(
    "/codename", status_code=status.HTTP_201_CREATED, response_model=AffiliateCodename
)
def set_codename(
    codename: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    AffiliateService.set_codename(db, current_user.user, codename)

    return {"message": "Codename set successfully", "codename": codename}


@affiliate.get("/referral", status_code=status.HTTP_200_OK)
def get_referral_link(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    return AffiliateService.get_referral_code(db, current_user.user)


@affiliate.get("/all")
def get_all_affiliates(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    return AffiliateService.get_all(db)


@affiliate.get("/commissions", status_code=status.HTTP_200_OK)
def get_commissions(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    return AffiliateService.get_commissions(db, current_user.user.id, page, limit)


@affiliate.get("/commissions/export", response_class=Response)
def export_commissions(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    content = AffiliateService.export_commissions(db, current_user.user.id)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=commissions.xlsx"},
    )


@affiliate.post(
    "/payout", status_code=status.HTTP_201_CREATED, response_model=NewPayoutResponse
)
def post_payout(
    create_request: PayoutRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    payout = PayoutService.create_new(db, create_request, current_user.user.id)
    # current_user here is the affiliate, not an ERP user — the notification is
    # for the staff who can act on the request
    ERPService.notify_permission_holders(
        db,
        PermissionEnum.APPROVE_AFFILIATE_PAYOUTS,
        message="Affiliate Payout Request",
        reference_type=NotificationReferenceTypeEnum.PAYOUT,
        amount=create_request.amount,
        method=PayoutMethodEnum.bank_transfer,
        affiliate_id=payout.affiliate_id,
        reference_id=payout.id
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
    current_user: CurrentUser = Depends(require_roles("affiliate")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[PayoutStatusEnum] = Query(None, description="Payout Status"),
):
    return AffiliateService.get_payouts(db, current_user.user.id, page, limit, status)


@affiliate.get("/payouts/export", response_class=Response)
def export_payouts(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
    status: Optional[PayoutStatusEnum] = Query(None, description="Payout Status"),
):

    content = AffiliateService.export_payouts(db, current_user.user.id, status)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=payouts.xlsx"},
    )


@affiliate.get(
    "/payouts/summary", status_code=status.HTTP_200_OK, response_model=PayoutSummary
)
def get_payouts_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    return AffiliateService.get_payouts_summary(db, current_user.user.id)


@affiliate.post("/visits", status_code=status.HTTP_200_OK)
def record_visitor(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    AffiliateService.record_unique_visit(db, current_user.user, request, response)

    return {"message": "Affiliate referral recorded."}


@affiliate.post(
    "/me/bank-details",
    status_code=status.HTTP_201_CREATED,
    response_model=UpdateBankDetailsResponse,
)
def add_bank_details(
    bank_details: UpdateBankDetailsRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    AffiliateService.add_bank_details(db, current_user.user, bank_details)

    return {
        "message": "Bank details created successfully",
        "bank_name": bank_details.bank_name,
        "account_number": bank_details.account_number,
    }
