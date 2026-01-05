from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Union
from uuid import UUID

from app.core.enums import TransactionStatusEnum, ServiceTypeEnum
from app.schemas.customer import CustomerResponse


class TransactionBase(BaseModel):
    transaction_type: str
    commission_rate: Decimal
    commission_amount: Decimal
    status: TransactionStatusEnum
    customer_id: UUID
    affiliate_source: Optional[str] = None


class BaseTransactionCreate(BaseModel):
    # service_type: ServiceTypeEnum
    amount_in: Decimal
    # transaction_type: str
    # commission_rate: Decimal
    # commission_amount: Decimal
    # status: TransactionStatusEnum

    customer_id: UUID
    affiliate_source: Optional[str] = None


class CryptoTransactionCreate(BaseTransactionCreate):
    service_type: ServiceTypeEnum = ServiceTypeEnum.crypto
    crypto_pair: str

    vendor_rate: Decimal
    xbanka_rate: Decimal
    margin: Decimal


class GiftCardTransactionCreate(BaseTransactionCreate):
    service_type: ServiceTypeEnum = ServiceTypeEnum.gift_card
    gift_card_type: str
    currency: str
    quantity: int

    vendor_rate: Decimal
    xbanka_rate: Decimal
    margin: Decimal


class BillPaymentTransactionCreate(BaseTransactionCreate):
    service_type: ServiceTypeEnum = ServiceTypeEnum.bill_payments
    biller_category: str


TransactionCreatePayload = Union[
    CryptoTransactionCreate,
    GiftCardTransactionCreate,
    BillPaymentTransactionCreate
]


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