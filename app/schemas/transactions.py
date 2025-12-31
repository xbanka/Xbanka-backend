from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID

from app.core.enums import TransactionStatusEnum
from app.schemas.customer import CustomerResponse


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    transaction_type: str
    commission_rate: Decimal
    commission_amount: Decimal
    status: TransactionStatusEnum
    customer: CustomerResponse
    affiliate_source: Optional[str] = None

class PaginatedTransactionResponse(BaseModel):
    page: int
    limit: int
    total: int
    pages: int
    data: List[TransactionResponse]