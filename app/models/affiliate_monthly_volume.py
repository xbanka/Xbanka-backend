from datetime import date
from decimal import Decimal
from app.models.base_model import BaseModel
from sqlalchemy import ForeignKey, String, Enum, DECIMAL, Computed, Numeric, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AffiliateMonthlyVolume(BaseModel):
    __tablename__ = 'affiliate_monthly_volume'

    __table_args__ = (
        UniqueConstraint('affiliate_id', 'month', name='uix_affiliate_monthly_volume'),
    )

    affiliate_id: Mapped[UUID] = mapped_column(ForeignKey('affiliates.id'), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # Format: 'YYYY-MM'
    total_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0.00)
    total_commission: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0.00)

    affiliate = relationship("Affiliate", back_populates="monthly_volumes")

    def __repr__(self):
        return (
            f"<AffiliateMonthlyVolume(id={self.id}, affiliate_id={self.affiliate_id}, "
            f"month='{self.month}', total_volume={self.total_volume})>"
        )