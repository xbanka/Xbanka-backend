from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Discriminator, model_validator, Tag
from typing import Annotated, List, Literal, Optional, Union
from uuid import UUID

from app.core.enums import TransactionStatusEnum, ServiceTypeEnum, CryptoPairEnum, UploadStatusEnum


class TransactionBase(BaseModel):
    id: UUID
    created_at: datetime
    commission_rate: Decimal
    commission_amount: Decimal
    status: TransactionStatusEnum
    upload_status: UploadStatusEnum
    vendor_rate: float
    xbanka_rate: float
    margin: float
    attachment_url: str
    affiliate_source: Optional[str] = None


class BaseTransactionCreate(BaseModel):
    @model_validator(mode="after")
    def validate_single_service(self):
        return self
    # service_type: ServiceTypeEnum
    amount_in: Decimal
    vendor: str
    customer_account: str

    customer_id: UUID
    affiliate_source: Optional[str] = None

class CryptoTransactionCreate(BaseTransactionCreate):
    service_type: Literal[ServiceTypeEnum.crypto]
    crypto_pair: CryptoPairEnum
    xbanka_account: str

    vendor_rate: Decimal
    xbanka_rate: Decimal


class GiftCardTransactionCreate(BaseTransactionCreate):
    service_type: Literal[ServiceTypeEnum.gift_card]
    gift_card_type: str
    gift_card_code: str
    currency: str
    quantity: int

    vendor_rate: Decimal
    xbanka_rate: Decimal


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
    Discriminator('service_type')
]


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    transaction: TransactionBase
    


class PaginatedTransactionResponse(BaseModel):
    page: int
    limit: int
    total: int
    pages: int
    data: List[TransactionBase]