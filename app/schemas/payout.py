from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class PayoutBase(BaseModel):
    amount: float | str
    bank: str
    payment_ref: Optional[str] = None

    @field_validator("amount", mode="before")
    def parse_amount(cls, v):
        if isinstance(v, str):
            v = v.replace(",", "")  # remove commas
        return float(v)

class NewPayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    payout: PayoutBase

class PayoutSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_earnings: float
    pending_payouts: float
    amount_withdrawn: float
    available_balance: float

    