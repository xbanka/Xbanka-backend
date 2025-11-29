from app.core.enums import NotificationTypeEnum, PayoutMethodEnum
from app.models.base_model import BaseModel
from sqlalchemy import String, Enum, ForeignKey, Boolean, DateTime, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional

class Notification(BaseModel):
    __tablename__ = 'notifications'

    message: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[NotificationTypeEnum] = mapped_column(Enum(NotificationTypeEnum), nullable=False, default=NotificationTypeEnum.system, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    method: Mapped[Optional[PayoutMethodEnum]] = mapped_column(Enum(PayoutMethodEnum), nullable=False, index=True)

    affiliate_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("affiliates.id"), nullable=True, index=True)

    affiliate = relationship("Affiliate", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(message='{self.message}', type='{self.type}', user_id={self.user_id})>"