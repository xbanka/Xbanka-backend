from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import PayoutStatusEnum, UploadStatusEnum
from app.schemas.affiliate import AffiliateSummaryResponse, AffiliatePayoutResponse



class ERPPayoutDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    status: PayoutStatusEnum
    payment_ref: str
    paid_at: Optional[datetime] = None
    bank: str
    affiliate: AffiliatePayoutResponse
    upload_status: UploadStatusEnum
    notes: Optional[str] = None
    attachment_url: Optional[str] = None

class ERPPayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    status: PayoutStatusEnum
    payment_ref: str
    paid_at: Optional[datetime] = None
    bank: str
    affiliate: AffiliateSummaryResponse
    upload_status: UploadStatusEnum
    notes: Optional[str] = None
    attachment_url: Optional[str] = None


class ERPPaginatedPayoutResponse(BaseModel):
    page: int
    limit: int
    total: int
    pages: int
    data: List[ERPPayoutResponse]


class ERPProcessPayoutResponse(BaseModel):
    message: str
    payout: ERPPayoutResponse
