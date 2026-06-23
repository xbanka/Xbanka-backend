from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.customer import (
    CustomerCreateBase,
    CustomerCreateResponse,
    CustomerResponse,
)
from app.services.core_backend import CoreBackendService
from app.services.customer import CustomerService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

customer = APIRouter(prefix="/customers", tags=["Customers"])


@customer.post(
    "/new", response_model=CustomerCreateResponse, status_code=status.HTTP_201_CREATED
)
def create_customer(
    customer_request: CustomerCreateBase,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp")),
):
    customer = CustomerService.create(db, customer_request)
    return {"message": "Customer created successfully", "customer": customer}


@customer.post(
    "/new/public",
    response_model=CustomerCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_public(
    customer_request: CustomerCreateBase, db: Session = Depends(get_db)
):
    customer = CustomerService.create(db, customer_request)
    return {"message": "Customer created successfully", "customer": customer}


@customer.get(
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
        return CoreBackendService.get_all_users(
            page=page, 
            limit=limit,
            search=search,
            status=status_filter,
            startDate=start_date,
            endDate=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@customer.get(
    "/search", status_code=status.HTTP_200_OK
)
def search_customers(
    q: str = Query(...), 
    current_user: CurrentUser = Depends(require_roles("affiliate", "erp", "super"))
):
    try:
        return CoreBackendService.search_users(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@customer.get("/{customer_id:uuid}", status_code=status.HTTP_200_OK)
def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    return CoreBackendService.get_user_by_id(customer_id)


@customer.delete("/{customer_id}", status_code=status.HTTP_200_OK)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("super")),
):
    CustomerService.delete_customer(db, customer_id)
    return {"message": "Customer deleted successfully."}
