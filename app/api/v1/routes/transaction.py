from app.db.database import get_db
from app.schemas.transactions import TransactionCreatePayload
from app.services.transaction import TransactionService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session


transaction = APIRouter(prefix="/transactions", tags=["Transactions"])

@transaction.get("/status", status_code=status.HTTP_200_OK)
def transaction_status():
    return {"status": "Transaction route is operational"}

@transaction.post("/new", status_code=status.HTTP_201_CREATED)
def create_transaction(
    trans_request: TransactionCreatePayload, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp"))
):

    TransactionService.create(obj_in=trans_request, db=db)
    return {"message": "Transaction created successfully"}