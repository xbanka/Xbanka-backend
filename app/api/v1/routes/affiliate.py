from typing import List
from fastapi import APIRouter, status, Depends, Query, Response, HTTPException
from app.models.transactions import Transaction
from app.schemas.affiliate import AffiliateCodename, PaginatedTransactionResponse
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.db.database import get_db
from app.models import Affiliate
from sqlalchemy.orm import Session

# from openpyxl import Workbook
# from io import BytesIO

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
):
    return AffiliateService.get_commissions(db, current_user.id, page, limit)


# @affiliate.get("/commssions/export", response_class=Response)
# def export_commissions(db: Session = Depends(get_db)):
#     commissions = db.query(Transaction).all()

#     wb = Workbook()
#     ws = wb.active or wb.create_sheet(title="Commissions")
#     # if not ws:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#     #         detail="Failed to create Excel worksheet" 
#     #     )
    
#     ws.title = "Transactions"

#     ws.append(["Date", "Type", "Rate", "Amount", "Status"])  # header
#     for tx in commissions:
#         ws.append([
#             tx.date,
#             tx.transaction_type,
#             tx.commission_rate,
#             tx.commission_amount,
#             tx.status,
#         ])

#     stream = BytesIO()
#     wb.save(stream)
#     stream.seek(0)

#     return Response(
#         content=stream.getvalue(),
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={"Content-Disposition": "attachment; filename=transactions.xlsx"}
#     )
