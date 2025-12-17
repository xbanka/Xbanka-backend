from uuid import UUID
from app.services.customer import CustomerService
from app.db.database import get_db
from app.schemas.customer import CustomerBase, CustomerCreateResponse, MockCustomerResponse
from fastapi import Query

from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session
from typing import List


customer = APIRouter(prefix="/customers", tags=["Customers"])

@customer.post(
    "/new", 
    response_model=CustomerCreateResponse, 
    status_code=status.HTTP_201_CREATED
)
def create_customer(customer_request: CustomerBase, db: Session = Depends(get_db)):
    customer = CustomerService.create(db, customer_request)
    return {"message": "Customer created successfully", "customer": customer}


@customer.get("/all", response_model=List[MockCustomerResponse])
def fetch_all_customers(db: Session = Depends(get_db)):
    customers = CustomerService.fetch_all(db)
    return customers


@customer.get(
    "/search", 
    response_model=List[MockCustomerResponse],
    status_code=status.HTTP_200_OK
)
def search_customers(q: str = Query(...), db: Session = Depends(get_db)):
    customers = CustomerService.search_customers(db, q)
    return customers


@customer.get("/{customer_id}", response_model=MockCustomerResponse)
def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    customers = CustomerService.fetch(db, customer_id)
    return customers