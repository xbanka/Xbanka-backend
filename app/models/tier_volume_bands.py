from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class TierVolumeBand(BaseModel):
    __tablename__ = "tier_volume_bands"

    tier_name: Mapped[str] = mapped_column(String, nullable=False)
    tier_id: Mapped[UUID] = mapped_column(
        ForeignKey("affiliate_tiers.id"), nullable=False, index=True
    )
    min_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )  # e.g., 5.00 for 5%

    tier = relationship("AffiliateTier", back_populates="volume_bands")

    def __repr__(self):
        return (
            f"<TierVolumeBand(id={self.id}, tier_name='{self.tier_name}', "
            f"min_volume={self.min_volume}, max_volume={self.max_volume}, "
            f"commission_rate={self.commission_rate}%)>"
        )
