from decimal import Decimal
from pydantic import BaseModel, ConfigDict


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
