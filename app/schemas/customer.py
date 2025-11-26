from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional

class CustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str
    phone_no: str
    transaction_type: str
    amount: str
    note: Optional[str] = None


class MockBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    first_name: str
    first_name: str
    email: str
    phone_no: str
    commission: float


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    first_name: str
    email: str
    phone_no: str
    commission: float


class MockCustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    phone_no: str
    transaction_type: str
    amount: str
    note: Optional[str] = None


class CustomerCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    customer: MockCustomerBase