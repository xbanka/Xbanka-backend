from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional
from app.schemas.affiliate import AffiliateMeResponse

class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str
    affiliate: Optional[AffiliateMeResponse] = None
    note: Optional[str] = None


class CustomerBrief(BaseModel):
    """Minimal customer representation for transaction-related responses"""
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str

class CustomerCreateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str
    affiliate_username: Optional[str] = None
    note: Optional[str] = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    phone_no: str
    affiliate: Optional[AffiliateMeResponse] = None


class CustomerCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    customer: CustomerRead