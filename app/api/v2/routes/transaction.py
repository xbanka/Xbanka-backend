from fastapi import APIRouter, Depends, Query, Body, status, HTTPException

from app.utils.auth import require_account_type
from app.utils.schema import CurrentUser
from app.services.internal_backend import InternalAPIService

transaction_v2 = APIRouter(prefix="/transactions", tags=["Transactions v2"])

@transaction_v2.get(
    "/all", status_code=status.HTTP_200_OK
)
def fetch_all_transactions(
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super")),
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


@transaction_v2.post(
    "/manual-log", status_code=status.HTTP_201_CREATED
)
def create_manual_transaction_log(
    payload: dict = Body(...),
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super")),
):
    try:
        return InternalAPIService.log_manual_transaction(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
