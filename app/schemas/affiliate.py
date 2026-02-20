from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
from uuid import UUID
from app.core.enums import PayoutStatusEnum



class AffiliateSummaryResponse(BaseModel):
    """used when an affiliate is represented as a nested object in another response, e.g. in customer details"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    username: Optional[str] = None
    created_at: datetime


class AffiliateTierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    is_restricted: bool

class BankDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bank_name: str
    account_number: str

class VolumeBandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_volume: Decimal
    max_volume: Optional[Decimal]
    commission_rate: Decimal


class AffiliateProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_monthly_volume: Decimal
    current_band: Optional[VolumeBandResponse]
    next_band: Optional[VolumeBandResponse]
    next_tier: Optional[AffiliateTierResponse]
    amount_to_next_band: Optional[Decimal]


class AffiliateMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    username: Optional[str] = None
    phone_no: str
    ref_code: str
    custom_refcode: Optional[str] = None
    created_at: datetime
    bank_details: List[BankDetailsResponse]
    current_tier: AffiliateTierResponse
    progress: AffiliateProgressResponse

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
