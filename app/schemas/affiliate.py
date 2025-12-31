from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
from uuid import UUID

from app.core.enums import PayoutStatusEnum


class AffiliateMeResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    username: Optional[str] = None
    phone_no: str
    bank: str
    account_no: str
    ref_code: str
    custom_refcode: Optional[str] = None
    created_at: datetime

class AffiliateCodename(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    codename: str

class PayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    status: PayoutStatusEnum
    payment_ref: str
    paid_at: datetime


class PaginatedPayoutResponse(BaseModel):
    page: int
    limit: int
    total: int
    pages: int
    data: List[PayoutResponse]


class UpdateBankDetailsRequest(BaseModel):
    bank_name: str
    account_number: str


class UpdateBankDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    bank_name: str
    account_number: str
