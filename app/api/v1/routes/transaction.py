from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.enums import Permission
from app.db.database import get_db
from app.schemas.transactions import (
    FundingCreditRequest,
    FundingIntentCompleteRequest,
    FundingIntentRejectRequest,
    AccountLookupRequest,
    TransactionCreateResponse,
    XbankaAccountCreateRequest,
    XbankaAccountUpdateRequest,
)
from app.services.internal_backend import InternalAPIService
from app.services.transaction import TransactionService
from app.utils.auth import require_account_type, require_permissions
from app.utils.schema import CurrentUser

transaction = APIRouter(prefix="/transactions", tags=["Transactions"])


CREATE_TRANSACTIONS = Permission.CREATE_TRANSACTIONS
VIEW_TRANSACTIONS = Permission.VIEW_TRANSACTIONS
EXPORT_TRANSACTIONS = Permission.EXPORT_TRANSACTIONS
ADJUST_BALANCE = Permission.ADJUST_BALANCE
VIEW_PAYMENTS = Permission.VIEW_PAYMENTS

@transaction.get(
    "/all", status_code=status.HTTP_200_OK
)
def fetch_all_transactions(
    current_user: CurrentUser = Depends(require_permissions(VIEW_TRANSACTIONS)),
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.get("/export", status_code=status.HTTP_200_OK, response_class=Response)
def export_transactions(
    current_user: CurrentUser = Depends(require_permissions(EXPORT_TRANSACTIONS)),
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
    except HTTPException:
        raise
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
    current_user: CurrentUser = Depends(require_permissions(VIEW_TRANSACTIONS)),
):
    return InternalAPIService.get_transaction_by_id(transaction_id)

    
@transaction.post(
    "/manual-log", status_code=status.HTTP_201_CREATED
)
def create_manual_transaction_log(
    payload: dict,
    current_user: CurrentUser = Depends(require_permissions(CREATE_TRANSACTIONS)),
):
    try:
        return InternalAPIService.log_manual_transaction(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.get("/funding/credits", status_code=status.HTTP_200_OK)
def fetch_funding_credits(
    current_user: CurrentUser = Depends(require_permissions(VIEW_PAYMENTS)),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    try:
        return InternalAPIService.get_funding_credits(page=page, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.post("/funding/credit", status_code=status.HTTP_200_OK)
def credit_funding_account(
    payload: FundingCreditRequest,
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    try:
        return InternalAPIService.credit_funding_account(
            payload.model_dump(mode="json")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.get("/funding/banks", status_code=status.HTTP_200_OK)
def fetch_funding_banks(
    current_user: CurrentUser = Depends(require_permissions(VIEW_PAYMENTS)),
):
    try:
        return InternalAPIService.get_funding_banks()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.post("/funding/accounts/lookup", status_code=status.HTTP_200_OK)
def lookup_funding_account(
    payload: AccountLookupRequest,
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    try:
        return InternalAPIService.lookup_funding_account(payload.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.get("/funding/xbanka-accounts", status_code=status.HTTP_200_OK)
def fetch_xbanka_accounts(
    current_user: CurrentUser = Depends(require_permissions(VIEW_PAYMENTS)),
):
    try:
        return InternalAPIService.get_xbanka_accounts()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.post("/funding/xbanka-accounts", status_code=status.HTTP_200_OK)
def create_xbanka_account(
    payload: XbankaAccountCreateRequest,
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    try:
        return InternalAPIService.create_xbanka_account(payload.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.patch("/funding/xbanka-accounts/{account_id}", status_code=status.HTTP_200_OK)
def update_xbanka_account(
    account_id: UUID,
    payload: XbankaAccountUpdateRequest,
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    """Edit details, hide from customers (`isActive: false`) or make primary (`isPrimary: true`)."""
    try:
        return InternalAPIService.update_xbanka_account(
            account_id, payload.model_dump(mode="json", exclude_unset=True)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.delete("/funding/xbanka-accounts/{account_id}", status_code=status.HTTP_200_OK)
def delete_xbanka_account(
    account_id: UUID,
    deleted_by: str = Query(..., alias="deletedBy", min_length=1, description="Email of the staff member deleting the account"),
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    """The primary account can't be deleted; make another account primary first."""
    try:
        return InternalAPIService.delete_xbanka_account(account_id, deleted_by)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.get("/funding/intents", status_code=status.HTTP_200_OK)
def fetch_funding_intents(
    current_user: CurrentUser = Depends(require_permissions(VIEW_PAYMENTS)),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    account_number: str = Query(
        None,
        alias="accountNumber",
        pattern=r"^\d{10}$",
        description="Sender account number (10 digits) registered by the customer",
    ),
    status_filter: str = Query(
        None, alias="status", description="PENDING (default), COMPLETED or FAILED"
    ),
):
    try:
        return InternalAPIService.get_funding_intents(
            page=page,
            limit=limit,
            accountNumber=account_number,
            status=status_filter,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.post("/funding/intents/{transaction_id}/complete", status_code=status.HTTP_200_OK)
def complete_funding_intent(
    transaction_id: UUID,
    payload: FundingIntentCompleteRequest,
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    try:
        return InternalAPIService.complete_funding_intent(
            transaction_id, payload.model_dump(mode="json", exclude_none=True)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.post("/funding/intents/{transaction_id}/reject", status_code=status.HTTP_200_OK)
def reject_funding_intent(
    transaction_id: UUID,
    payload: FundingIntentRejectRequest,
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    try:
        return InternalAPIService.reject_funding_intent(
            transaction_id, payload.model_dump(mode="json")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transaction.post("/funding/attachments", status_code=status.HTTP_200_OK)
def upload_funding_attachment(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions(ADJUST_BALANCE)),
):
    try:
        return InternalAPIService.upload_funding_attachment(
            file.filename or "attachment", file.file.read(), file.content_type
        )
    except HTTPException:
        raise
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
    current_user: CurrentUser = Depends(require_account_type("erp")),
):
    transaction = TransactionService.upload_attachment(
        db=db, transaction_id=transaction_id, attachment=attachment
    )
    return {"message": "Attachment uploaded successfully", "transaction": transaction}
