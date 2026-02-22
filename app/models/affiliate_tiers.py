from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class AffiliateTier(BaseModel):
    __tablename__ = "affiliate_tiers"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    is_restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank = mapped_column(
        Integer, nullable=True, unique=True
    )  # higher rank means higher tier

    volume_bands = relationship("TierVolumeBand", back_populates="tier")

    affiliates = relationship("Affiliate", back_populates="current_tier")

    def __repr__(self):
        return f"<AffiliateTier(id={self.id}, name='{self.name}', description='{self.description}', is_restricted={self.is_restricted})>"
