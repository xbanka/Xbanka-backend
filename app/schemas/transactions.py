from datetime import datetime
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import Annotated, List, Literal, Optional, Union
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    Discriminator,
    PlainSerializer,
    Tag,
    computed_field,
    model_validator,
)

from app.core.enums import CryptoPairEnum, ServiceTypeEnum, TxnStatusEnum, UploadStatusEnum
from app.schemas.customer import CustomerBrief, CustomerRead


def _decimal_as_json_number(value: Decimal) -> Union[int, float]:
    """pydantic's mode="json" turns Decimal into a string, but the core validates
    these amounts with @IsNumber (no string coercion). Send a real JSON number:
    an int when the value is whole (1000, not 1000.0), otherwise the float, whose
    shortest repr round-trips cleanly (0.1 stays 0.1)."""
    if value == value.to_integral_value():
        return int(value)
    return float(value)


_CENT = Decimal("0.01")


def _trim_to_two_places(value: Decimal) -> Decimal:
    """The core allows at most 2 decimal places (@IsNumber maxDecimalPlaces: 2) and
    a minimum of 0.01. Cut any overflow toward zero (never credit more than was
    entered) and refuse an amount that trims to nothing, e.g. 0.001."""
    try:
        trimmed = value.quantize(_CENT, rounding=ROUND_DOWN)
    except InvalidOperation:
        raise ValueError("amount is too large")
    if trimmed < _CENT:
        raise ValueError("amount must be at least 0.01")
    return trimmed


# Validated and trimmed as an exact Decimal (no float math on input); only the
# JSON dump turns it into a number.
JsonNumberDecimal = Annotated[
    Decimal,
    AfterValidator(_trim_to_two_places),
    PlainSerializer(_decimal_as_json_number, when_used="json"),
]


class TransactionMetaData(BaseModel):
    isManual: bool = True
    paymentMethod: str
    partnerRate: float
    xbankaRate: float
    marginPercentage: str

class LogManualTransactionsRequest(BaseModel):
    email: str
    firstName: str
    lastName: str
    transactionType: str
    amount: float
    currency: str
    status: TxnStatusEnum
    metadata: TransactionMetaData


class FundingCreditRequest(BaseModel):
    fundingAccountId: UUID
    amount: JsonNumberDecimal = Field(gt=0)
    reference: str
    creditedBy: str
    attachmentUrls: List[str] = Field(default_factory=list)


class AccountLookupRequest(BaseModel):
    accountNumber: str = Field(pattern=r"^\d{10}$")
    bankCode: str = Field(min_length=1)


class XbankaAccountCreateRequest(BaseModel):
    bankName: str = Field(min_length=1)
    bankCode: str = Field(min_length=1)
    accountNumber: str = Field(pattern=r"^\d{10}$")
    accountName: str = Field(min_length=1)
    isPrimary: bool = False
    updatedBy: str


class XbankaAccountUpdateRequest(BaseModel):
    bankName: Optional[str] = Field(default=None, min_length=1)
    bankCode: Optional[str] = Field(default=None, min_length=1)
    accountNumber: Optional[str] = Field(default=None, pattern=r"^\d{10}$")
    accountName: Optional[str] = Field(default=None, min_length=1)
    isPrimary: Optional[bool] = None
    isActive: Optional[bool] = None
    updatedBy: str

    @model_validator(mode="after")
    def _require_a_change(self):
        if not self.model_fields_set - {"updatedBy"}:
            raise ValueError("Provide at least one field to update")
        return self


class FundingIntentCompleteRequest(BaseModel):
    bankReference: str = Field(min_length=1)
    creditedBy: str
    # defaults to the amount the customer declared; overrideReason is required with it
    amount: Optional[JsonNumberDecimal] = Field(default=None, gt=0)
    overrideReason: Optional[str] = None
    fundingAccountId: Optional[UUID] = None
    attachmentUrls: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_reason_for_override(self):
        if self.amount is not None and not self.overrideReason:
            raise ValueError("overrideReason is required when amount is provided")
        return self


class FundingIntentRejectRequest(BaseModel):
    rejectedBy: str
    reason: str = Field(min_length=1)


class TransactionDetailResponse(BaseModel):
    id: UUID
    txn_id: str
    created_at: datetime
    service_type: ServiceTypeEnum
    gift_card_type: Optional[str] = None
    amount_in: Decimal
    amount_out: Decimal
    vendor: str
    crypto_pair: Optional[str] = None
    gift_card_code: Optional[str] = None
    currency_in: str
    currency_out: str
    commission_rate: Decimal
    commission_amount: Decimal
    upload_status: UploadStatusEnum
    vendor_rate: Optional[float] = None
    xbanka_rate: Optional[float] = None
    margin: Optional[float] = None
    attachment_url: str
    affiliate_source: Optional[str] = None
    customer: CustomerRead


class TransactionBrief(BaseModel):
    id: UUID
    txn_id: str
    created_at: datetime
    service_type: ServiceTypeEnum
    amount_in: Decimal
    amount_out: Decimal
    vendor: str
    currency_in: str
    currency_out: str
    vendor_rate: Optional[float] = None
    xbanka_rate: Optional[float] = None
    margin: Optional[float] = None
    attachment_url: str
    affiliate_source: Optional[str] = None
    customer: CustomerBrief
    crypto_pair: Optional[str] = None
    gift_card_type: Optional[str] = None

    @computed_field
    @property
    def transaction_type(self) -> str:
        if self.crypto_pair:
            return self.crypto_pair
        if self.gift_card_type:
            return self.gift_card_type
        raise ValueError("Invalid transaction: neither crypto_pair nor card_type set")


class BaseTransactionCreate(BaseModel):
    @model_validator(mode="after")
    def validate_single_service(self):
        return self

    amount_in: Decimal
    vendor: str
    customer_account: str

    customer_id: UUID


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


def get_service_type(
    v: Union[
        CryptoTransactionCreate, GiftCardTransactionCreate, BillPaymentTransactionCreate
    ],
) -> str:
    return v.service_type.value


TransactionCreatePayload = Annotated[
    Union[
        Annotated[CryptoTransactionCreate, Tag(ServiceTypeEnum.crypto.value)],
        Annotated[GiftCardTransactionCreate, Tag(ServiceTypeEnum.gift_card.value)],
        Annotated[
            BillPaymentTransactionCreate, Tag(ServiceTypeEnum.bill_payments.value)
        ],
    ],
    Discriminator("service_type"),
]


class TransactionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    transaction: TransactionBrief


class PaginatedTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int
    limit: int
    total: int
    pages: int
    data: List[TransactionBrief]
