from typing import Optional
from app.core.enums import StatusEnum
from app.schemas.affiliate import AffiliateCodename, PaginatedTransactionResponse
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.db.database import get_db
from app.models import Affiliate

from fastapi import APIRouter, status, Depends, Query, Response
from sqlalchemy.orm import Session


affiliate = APIRouter(prefix="/affiliates", tags=["Affiliates"])

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
    status: Optional[StatusEnum] = Query(None, description="Commission Status")
):
    return AffiliateService.get_commissions(db, current_user.id, page, limit, status)


@affiliate.get("/commissions/export", response_class=Response)
def export_commissions(
    db: Session = Depends(get_db),
    current_user: Affiliate = Depends(AuthService.get_current_user),
    status: Optional[StatusEnum] = Query(None, description="Commission Status")
):
    
    content = AffiliateService.export_commissions(db, current_user.id, status)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=commissions.xlsx"}
    )
