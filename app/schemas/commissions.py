


from typing import List
from pydantic import BaseModel, ConfigDict


class CommissionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    txn_id: str
    created_at: str
    service_type: str
    amount_in: float
    amount_out: float
    vendor: str
    currency_in: str
    currency_out: str
    commission_rate: float
    commission_amount: float

class PaginatedCommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int
    limit: int
    total: int
    pages: int
    data: List[CommissionBrief]