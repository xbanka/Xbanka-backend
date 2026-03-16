from decimal import Decimal

from sqlalchemy import DECIMAL, Computed, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CryptoPairEnum, ServiceTypeEnum, TransactionStatusEnum, UploadStatusEnum
from app.models.base_model import BaseModel


class Transaction(BaseModel):
    __tablename__ = "transactions"

    txn_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    affiliate_source: Mapped[str] = mapped_column(String, nullable=True)
    # transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    service_type: Mapped[ServiceTypeEnum] = mapped_column(
        Enum(ServiceTypeEnum), nullable=False
    )
    # amount: Mapped[int] = mapped_column(DECIMAL(12, 2), nullable=False)
    amount_in: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_out: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=True
    )  # expected payout
    currency_in: Mapped[str] = mapped_column(String, nullable=True)
    currency_out: Mapped[str] = mapped_column(String, nullable=True)
    commission_rate: Mapped[float] = mapped_column(
        DECIMAL(12, 2), nullable=False, default=2.0
    )  # Default commission rate of 2%
    commission_amount: Mapped[int] = mapped_column(
        DECIMAL(12, 2),
        Computed("amount_in * commission_rate / 100", persisted=True),
        nullable=False,
    )
    status: Mapped[TransactionStatusEnum] = mapped_column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.pending, nullable=False)
    upload_status: Mapped[UploadStatusEnum] = mapped_column(Enum(UploadStatusEnum), default=UploadStatusEnum.pending, nullable=False)

    vendor: Mapped[str] = mapped_column(String, nullable=False)

    vendor_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    xbanka_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)

    margin: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        Computed("xbanka_rate - vendor_rate", persisted=True),
        nullable=True,
    )

    customer_account: Mapped[str] = mapped_column(String, nullable=True)

    # crypto-related fields
    crypto_pair: Mapped[CryptoPairEnum] = mapped_column(
        Enum(CryptoPairEnum), nullable=True
    )
    xbanka_account: Mapped[str] = mapped_column(String, nullable=True)

    # gift card-related fields
    gift_card_type: Mapped[str] = mapped_column(String, nullable=True)
    gift_card_code: Mapped[str] = mapped_column(String, nullable=True)
    quantity: Mapped[int] = mapped_column(Numeric(12, 2), nullable=True)

    attachment_url: Mapped[str] = mapped_column(String, nullable=True)

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )

    customer = relationship("Customer", back_populates="transactions")

    commission = relationship(
        "AffiliateCommission",
        back_populates="transaction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, customer_id={self.customer_id}, "
            f"transaction_type='{self.transaction_type}', commission_rate={self.commission_rate}, "
            f"commission_amount={self.commission_amount}, status='{self.status}')>"
        )
