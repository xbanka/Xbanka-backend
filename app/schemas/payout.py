from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PayoutRequest(BaseModel):
    amount: Decimal | str
    bank: str

    @field_validator("amount", mode="before")
    def parse_amount(cls, v):
        if isinstance(v, str):
            v = v.replace(",", "")  # remove commas
        return float(v)


class PayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: float
    bank: str
    payment_ref: str


class NewPayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    payout: PayoutResponse


class PayoutSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_earnings: float
    pending_payouts: float
    amount_withdrawn: float
    available_balance: float


class ProcessPayoutRequest(BaseModel):
    note: Optional[str] = None