from datetime import datetime
from decimal import Decimal
from fastapi import Body, UploadFile
from pydantic import BaseModel, ConfigDict, Discriminator, model_validator, Tag
from typing import Annotated, List, Literal, Optional, Union
from uuid import UUID

from app.core.enums import TransactionStatusEnum, ServiceTypeEnum, CryptoPairEnum
from app.schemas.customer import CustomerResponse


class TransactionBase(BaseModel):
    transaction_type: str
    commission_rate: Decimal
    commission_amount: Decimal
    status: TransactionStatusEnum
    customer_id: UUID
    affiliate_source: Optional[str] = None


class BaseTransactionCreate(BaseModel):
    @model_validator(mode="after")
    def validate_single_service(self):
        return self
    # service_type: ServiceTypeEnum
    amount_in: Decimal
    # transaction_type: str
    # commission_rate: Decimal
    # commission_amount: Decimal
    # status: TransactionStatusEnum

    customer_id: UUID
    affiliate_source: Optional[str] = None
    attachment: UploadFile


class CryptoTransactionCreate(BaseTransactionCreate):
    service_type: Literal[ServiceTypeEnum.crypto]
    crypto_pair: CryptoPairEnum

    vendor_rate: Decimal
    xbanka_rate: Decimal
    # margin: Decimal


class GiftCardTransactionCreate(BaseTransactionCreate):
    service_type: Literal[ServiceTypeEnum.gift_card]
    gift_card_type: str
    currency: str
    quantity: int

    vendor_rate: Decimal
    xbanka_rate: Decimal
    # margin: Decimal


class BillPaymentTransactionCreate(BaseTransactionCreate):
    service_type: Literal[ServiceTypeEnum.bill_payments]
    biller_category: str


# TransactionCreatePayload = Union[
#     CryptoTransactionCreate,
#     GiftCardTransactionCreate,
#     BillPaymentTransactionCreate
# ]

def get_service_type(v: Union[CryptoTransactionCreate, GiftCardTransactionCreate, BillPaymentTransactionCreate]) -> str:
    return v.service_type.value


TransactionCreatePayload = Annotated[
    Union[
        Annotated[CryptoTransactionCreate, Tag(ServiceTypeEnum.crypto.value)],
        Annotated[GiftCardTransactionCreate, Tag(ServiceTypeEnum.gift_card.value)],
        Annotated[BillPaymentTransactionCreate, Tag(ServiceTypeEnum.bill_payments.value)]
    ],
    Body(...),
    Discriminator('service_type')
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