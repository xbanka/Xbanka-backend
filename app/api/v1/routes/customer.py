from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.customer import (
    CustomerCreateBase,
    CustomerCreateResponse,
    CustomerResponse,
)
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


@customer.get("/all", response_model=List[CustomerResponse])
def fetch_all_customers(db: Session = Depends(get_db)):
    customers = CustomerService.fetch_all(db)
    return customers


@customer.get(
    "/search", response_model=List[CustomerResponse], status_code=status.HTTP_200_OK
)
def search_customers(q: str = Query(...), db: Session = Depends(get_db)):
    customers = CustomerService.search_customers(db, q)
    return customers


@customer.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    customers = CustomerService.fetch(db, customer_id)
    return customers


@customer.delete("/{customer_id}", status_code=status.HTTP_200_OK)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("super")),
):
    CustomerService.delete_customer(db, customer_id)
    return {"message": "Customer deleted successfully."}
