from typing import List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.transactions import (
    PaginatedTransactionResponse,
    TransactionBrief,
    TransactionCreatePayload,
    TransactionCreateResponse,
    TransactionDetailResponse,
)
from app.services.transaction import TransactionService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

transaction = APIRouter(prefix="/transactions", tags=["Transactions"])


@transaction.get(
    "/customer/{customer_id:uuid}",
    status_code=status.HTTP_200_OK,
    response_model=List[TransactionBrief],
)
def fetch_customer_transactions(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp")),
):
    return TransactionService.fetch_by_customer_paginated(db, customer_id)


@transaction.get(
    "/all", status_code=status.HTTP_200_OK, response_model=PaginatedTransactionResponse
)
def fetch_all_transactions(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    return TransactionService.fetch_all_paginated(db, page, limit)


@transaction.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionCreateResponse,
)
def create_transaction(
    trans_request: TransactionCreatePayload = Body(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp")),
):

    transaction = TransactionService.create(obj_in=trans_request, db=db)
    return {"message": "Transaction created successfully", "transaction": transaction}


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


@transaction.get(
    "/{transaction_id:uuid}",
    status_code=status.HTTP_200_OK,
    response_model=TransactionDetailResponse,
)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp")),
):
    return TransactionService.fetch(db, transaction_id)
