from pydantic import BaseModel, ConfigDict

class PayoutSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_earnings: float
    available_for_payout: float
    pending_payouts: float
    amount_withdrawn: float
    available_balance: float