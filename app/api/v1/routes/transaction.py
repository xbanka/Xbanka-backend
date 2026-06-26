from typing import List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.transactions import (
    TransactionBrief,
    TransactionCreatePayload,
    TransactionCreateResponse
)
from app.services.core_backend import CoreBackendService
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
        return CoreBackendService.get_all_transactions(
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
    

@transaction.get("/{transaction_id:uuid}", status_code=status.HTTP_200_OK)
def fetch_single_transaction(
    transaction_id: UUID, 
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super"))
):
    return CoreBackendService.get_transaction_by_id(transaction_id)

    
@transaction.post(
    "/manual-log", status_code=status.HTTP_201_CREATED
)
def create_manual_transaction_log(
    payload: dict,
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super")),
):
    try:
        return CoreBackendService.log_manual_transaction(payload)
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
