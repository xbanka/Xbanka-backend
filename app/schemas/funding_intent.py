from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SenderAccount(BaseModel):
    bankName: str
    accountNumber: str
    accountName: str


class FundingIntentDeclared(BaseModel):
    """Sent by the core backend when a customer taps "I have sent the money".

    camelCase to match the other payloads exchanged with the core backend
    (FundingIntentCompleteRequest and friends).
    """

    transactionId: UUID
    reference: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    customerName: Optional[str] = Field(default=None, max_length=200)
    customerXbId: Optional[str] = Field(default=None, max_length=50)
    declaredAt: Optional[datetime] = None
    registeredFundingAccounts: List[SenderAccount] = Field(default_factory=list)


class FundingIntentDeclaredResponse(BaseModel):
    notified: int
    duplicate: bool = False
