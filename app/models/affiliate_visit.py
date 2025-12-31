from app.models.base_model import BaseModel
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AffiliateVisit(BaseModel):
    __tablename__ = 'affiliate_visits'

    affiliate_id: Mapped[int] = mapped_column(ForeignKey('affiliates.id'), nullable=False, index=True)
    visitor_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=True)

    affiliate = relationship("Affiliate", back_populates="visits")