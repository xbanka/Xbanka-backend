from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID
from app.core.enums import TransactionStatusEnum, PayoutStatusEnum
from app.schemas.affiliate import AffiliateMeResponse

class ERPPayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    status: PayoutStatusEnum
    payment_ref: str
    paid_at: datetime
    affiliate: AffiliateMeResponse


class ERPPaginatedPayoutResponse(BaseModel):
    page: int
    limit: int
    total: int
    pages: int
    data: List[ERPPayoutResponse]