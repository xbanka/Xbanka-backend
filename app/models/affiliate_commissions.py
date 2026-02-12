from datetime import date
from sqlalchemy import Date, ForeignKey, String, Enum, DECIMAL, Computed, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base_model import BaseModel
from decimal import Decimal


class AffiliateCommission(BaseModel):
    __tablename__ = 'affiliate_commissions'

    __table_args__ = (
        UniqueConstraint('affiliate_id', 'transaction_id', name='uix_affiliate_transaction'),
    )

    affiliate_id: Mapped[UUID] = mapped_column(ForeignKey('affiliates.id'), nullable=False, index=True)
    transaction_id: Mapped[UUID] = mapped_column(ForeignKey('transactions.id'), nullable=False, index=True)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # e.g., 5.00 for 5%
    month: Mapped[date] = mapped_column(Date, nullable=False)  # Format: 'YYYY-MM'

    affiliate = relationship("Affiliate", back_populates="commissions")
    transaction = relationship("Transaction", back_populates="commission")

    def __repr__(self):
        return (
            f"<AffiliateCommission(id={self.id}, affiliate_id={self.affiliate_id}, "
            f"transaction_id={self.transaction_id}, commission_amount={self.commission_amount}, "
            f"commission_rate={self.commission_rate}%, month='{self.month}')>"
        )