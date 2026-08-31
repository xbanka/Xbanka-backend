from app.schemas.shared import ApiResponse

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field



class AffiliateDashboardDisplay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    visits: int
    signed_up: int
    converted: int
    total_commission: float


class RefundStats(BaseModel):
    count: int
    amount: float
    change: int

class ERPDashboardDisplay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transactions_today: int
    transactions_change_pct: float

    value_today: int
    value_change_pct: float
    
    failed_today: int
    failed_change: int

    refunds_today: RefundStats


class TransactionMetrics(BaseModel):
    total: int
    successful: int
    pending: int
    failed: int
    stuck_in_pending: int = Field(alias="stuckInPending")
    stuck_value: Optional[Decimal] = Field(default=None, alias="stuckValue")

TransactionMetricsResponse = ApiResponse[TransactionMetrics]

class CustomerMetrics(BaseModel):
    total: int
    new_today: int = Field(alias="newToday")
    kyc_pending: int = Field(alias="kycPending")
    flagged: int

CustomerMetricsResponse = ApiResponse[CustomerMetrics]