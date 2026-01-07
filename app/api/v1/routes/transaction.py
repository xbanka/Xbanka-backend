from uuid import UUID
from app.db.database import get_db
from app.schemas.transactions import PaginatedTransactionResponse, TransactionCreatePayload, TransactionResponse
from app.services.transaction import TransactionService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

from fastapi import APIRouter, Body, File, Query, UploadFile, status, Depends
from sqlalchemy.orm import Session


transaction = APIRouter(prefix="/transactions", tags=["Transactions"])


@transaction.get("/all", status_code=status.HTTP_200_OK, response_model=PaginatedTransactionResponse)
def fetch_all_transactions(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    return TransactionService.fetch_all_paginated(db, page, limit)


@transaction.post("/new", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse)
def create_transaction(
    trans_request: TransactionCreatePayload = Body(...), 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp"))
):

    transaction = TransactionService.create(obj_in=trans_request, db=db)
    return {"message": "Transaction created successfully", "transaction": transaction}


@transaction.post("/{transaction_id}/attachment", status_code=status.HTTP_200_OK, response_model=TransactionResponse)
def upload_transaction_attachment(
    transaction_id: UUID,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    transaction = TransactionService.upload_attachment(
        db=db, transaction_id=transaction_id, attachment=attachment
    )
    return {"message": "Attachment uploaded successfully", "transaction": transaction}


@transaction.get("/{transaction_id:uuid}", status_code=status.HTTP_200_OK)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp"))
):
    transaction = TransactionService.fetch(db, transaction_id)
    return {"transaction": transaction}
