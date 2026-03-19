from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PayoutStatusEnum, UploadStatusEnum
from app.models.base_model import BaseModel


class Payout(BaseModel):
    __tablename__ = "payouts"

    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    status: Mapped[PayoutStatusEnum] = mapped_column(
        Enum(PayoutStatusEnum), default=PayoutStatusEnum.pending, nullable=False
    )
    upload_status: Mapped[UploadStatusEnum] = mapped_column(Enum(UploadStatusEnum), default=UploadStatusEnum.pending, nullable=False)
    payment_ref: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    attachment_url: Mapped[str] = mapped_column(String, nullable=True)

    affiliate_id: Mapped[UUID] = mapped_column(
        ForeignKey("affiliates.id"), nullable=False, index=True
    )

    affiliate = relationship("Affiliate", back_populates="payouts")

    def __repr__(self):
        return (
            f"<Payout(id={self.id}, affiliate_id={self.affiliate_id}, "
            f"payment_ref='{self.payment_ref}', paid_at={self.paid_at}, "
            f"status='{self.status}')>"
        )
