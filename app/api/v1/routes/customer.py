from typing import Optional
from app.core.enums import PayoutStatusEnum, TransactionStatusEnum
from app.services.customer import CustomerService
from app.db.database import get_db
from app.schemas.customer import CustomerBase, CustomerCreateResponse

from fastapi import APIRouter, status, Depends, Query, Response
from sqlalchemy.orm import Session
customer = APIRouter(prefix="/customers", tags=["Customers"])

@customer.post("/new", 
    response_model=CustomerCreateResponse, 
    status_code=status.HTTP_201_CREATED
)
def create_customer(customer_request: CustomerBase, db: Session = Depends(get_db)):
    customer_service = CustomerService.create_customer(db, customer_request)
    customer = customer_service.create_customer(customer_request)
    return {"message": "Customer created successfully", "customer": customer}