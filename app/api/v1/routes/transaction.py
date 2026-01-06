import json
import logging
from typing import Annotated

from pydantic import ValidationError, parse_obj_as, TypeAdapter
from app.db.database import get_db
from app.schemas.transactions import TransactionCreatePayload
from app.services.transaction import TransactionService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

from fastapi import APIRouter, Body, File, Form, UploadFile, status, Depends, HTTPException
from sqlalchemy.orm import Session


transaction = APIRouter(prefix="/transactions", tags=["Transactions"])

@transaction.get("/status", status_code=status.HTTP_200_OK)
def transaction_status():
    return {"status": "Transaction route is operational"}

@transaction.post("/new", status_code=status.HTTP_201_CREATED)
def create_transaction(
    trans_request: Annotated[str, Form()],
    attachment: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp"))
):

    try:
        payload = json.loads(trans_request)
        item_data = TypeAdapter(TransactionCreatePayload)
        obj_in = item_data.validate_python(payload)
    except (json.JSONDecodeError, ValidationError) as e:
        logging.error(f"Transaction creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format in transaction request."
        )

    TransactionService.create(obj_in=obj_in, db=db)
    return {"message": "Transaction created successfully"}