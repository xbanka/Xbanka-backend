from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from app.services.internal_backend import InternalAPIService
from app.utils.auth import require_account_type
from app.utils.schema import CurrentUser

customer = APIRouter(prefix="/customers", tags=["Customers"])


@customer.get(
    "/all", status_code=status.HTTP_200_OK
)
def fetch_all_customers(
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super")),
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

@customer.get("/export", status_code=status.HTTP_200_OK, response_class=Response)
def export_customers(
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super")),
    search: str = Query(None, description="Search term for name, email, or phone"),
    status_filter: str = Query(None, alias="status", description="Filter by user status/step"),
    start_date: str = Query(None, alias="startDate", description="Start date (ISO)"),
    end_date: str = Query(None, alias="endDate", description="End date (ISO)"),
):
    try:
        content = InternalAPIService.export_customers(
            search=search,
            status=status_filter,
            startDate=start_date,
            endDate=end_date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=customers.xlsx"},
    )


@customer.get(
    "/search", status_code=status.HTTP_200_OK
)
def search_customers(
    q: str = Query(...), 
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super"))
):
    try:
        return InternalAPIService.search_users(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@customer.get("/{customer_id:uuid}", status_code=status.HTTP_200_OK)
def get_customer(customer_id: UUID, current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super"))):
    return InternalAPIService.get_user_by_id(customer_id)


@customer.get("/{customer_id:uuid}/transactions", status_code=status.HTTP_200_OK)
def get_customer_transactions(
    customer_id: UUID, 
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super")),
):
    try:
        return InternalAPIService.get_user_transactions(
            user_id=customer_id,
            page=page,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@customer.get("/{customer_id:uuid}/assets")
def get_customer_assets(
    customer_id: UUID,
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super"))
):
    try:
        return InternalAPIService.get_user_assets(user_id=customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@customer.get("/{customer_id:uuid}/verification")
def get_customer_verification(
    customer_id: UUID,
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super"))
):
    try:
        return InternalAPIService.get_user_verification_details(user_id=customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@customer.put("/{customer_id:uuid}/status")
def toggle_customer_status(
    customer_id: UUID,
    current_user: CurrentUser = Depends(require_account_type("affiliate", "erp", "super"))
):
    try:
        return InternalAPIService.toggle_user_status(user_id=customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@customer.get("/{customer_id:uuid}/kyc")
def get_customer_kyc(
    customer_id: UUID,
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super"))
):
    try:
        return InternalAPIService.get_user_kyc_details(user_id=customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
