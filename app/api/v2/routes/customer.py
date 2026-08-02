from fastapi import APIRouter, Depends, Query, status, HTTPException

from app.utils.auth import require_roles
from app.utils.schema import CurrentUser
from app.services.internal_backend import InternalAPIService

customer_v2 = APIRouter(prefix="/customers", tags=["Customers v2"])

@customer_v2.get(
    "/search", status_code=status.HTTP_200_OK
)
def search_customers(
    q: str = Query(...), 
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super"))
):
    try:
        return InternalAPIService.search_users(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@customer_v2.get(
    "/all", status_code=status.HTTP_200_OK
)
def fetch_all_customers(
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super")),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search term for name, email, or phone"),
    status_filter: str = Query(None, alias="status", description="Filter by user status/step"),
    start_date: str = Query(None, alias="startDate", description="Start date (ISO)"),
    end_date: str = Query(None, alias="endDate", description="End date (ISO)"),
):
    try:
        return InternalAPIService.get_all_users(
            page=page, 
            limit=limit,
            search=search,
            status=status_filter,
            startDate=start_date,
            endDate=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
