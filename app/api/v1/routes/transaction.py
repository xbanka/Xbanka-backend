from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.transactions import (
    TransactionCreateResponse
)
from app.services.internal_backend import InternalAPIService
from app.services.transaction import TransactionService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

transaction = APIRouter(prefix="/transactions", tags=["Transactions"])


@transaction.get(
    "/all", status_code=status.HTTP_200_OK
)
def fetch_all_transactions(
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search term for reference, name, or email"),
    status_filter: str = Query(None, alias="status", description="Filter by transaction status"),
    type: str = Query(None, description="Filter by transaction type"),
    currency: str = Query(None, description="Filter by currency"),
    category: str = Query(None, description="Filter by category (FIAT or CRYPTO)"),
    start_date: str = Query(None, alias="startDate", description="Start date (ISO)"),
    end_date: str = Query(None, alias="endDate", description="End date (ISO)"),
):
    try:
        return InternalAPIService.get_all_transactions(
            page=page, 
            limit=limit,
            search=search,
            status=status_filter,
            type=type,
            currency=currency,
            category=category,
            startDate=start_date,
            endDate=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.get("/export", status_code=status.HTTP_200_OK, response_class=Response)
def export_transactions(
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super")),
    search: str = Query(None, description="Search term for reference, name, or email"),
    status_filter: str = Query(None, alias="status", description="Filter by transaction status"),
    type: str = Query(None, description="Filter by transaction type"),
    currency: str = Query(None, description="Filter by currency"),
    category: str = Query(None, description="Filter by category (FIAT or CRYPTO)"),
    start_date: str = Query(None, alias="startDate", description="Start date (ISO)"),
    end_date: str = Query(None, alias="endDate", description="End date (ISO)"),
):
    try:
        content = InternalAPIService.export_transactions(
            search=search,
            status=status_filter,
            type=type,
            currency=currency,
            category=category,
            startDate=start_date,
            endDate=end_date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=transactions.xlsx"},
    )


@transaction.get("/{transaction_id:uuid}", status_code=status.HTTP_200_OK)
def fetch_single_transaction(
    transaction_id: UUID, 
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super"))
):
    return InternalAPIService.get_transaction_by_id(transaction_id)

    
@transaction.post(
    "/manual-log", status_code=status.HTTP_201_CREATED
)
def create_manual_transaction_log(
    payload: dict,
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super")),
):
    try:
        return InternalAPIService.log_manual_transaction(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@transaction.post(
    "/{transaction_id}/attachment",
    status_code=status.HTTP_200_OK,
    response_model=TransactionCreateResponse,
)
def upload_transaction_attachment(
    transaction_id: UUID,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    transaction = TransactionService.upload_attachment(
        db=db, transaction_id=transaction_id, attachment=attachment
    )
    return {"message": "Attachment uploaded successfully", "transaction": transaction}
