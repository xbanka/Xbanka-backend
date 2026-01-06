from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional
from app.schemas.affiliate import AffiliateMeResponse

class CustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str
    affiliate: Optional[AffiliateMeResponse] = None
    note: Optional[str] = None


class CustomerCreateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str
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


class MockCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    phone_no: str
    note: Optional[str] = None


class CustomerCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    customer: CustomerBase