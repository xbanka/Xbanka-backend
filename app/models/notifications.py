from datetime import datetime
from typing import Optional

from sqlalchemy import DECIMAL, Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    NotificationReferenceTypeEnum,
    NotificationStatusEnum,
    NotificationTypeEnum,
    PayoutMethodEnum,
)
from app.models.base_model import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[NotificationTypeEnum] = mapped_column(
        Enum(NotificationTypeEnum),
        nullable=False,
        default=NotificationTypeEnum.system,
        index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    amount: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    method: Mapped[Optional[PayoutMethodEnum]] = mapped_column(
        Enum(PayoutMethodEnum), nullable=True, index=True
    )
    reference_type: Mapped[NotificationReferenceTypeEnum] = mapped_column(
        Enum(NotificationReferenceTypeEnum), nullable=False, index=True
    )

    reference_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    status: Mapped[NotificationStatusEnum] = mapped_column(
        Enum(NotificationStatusEnum),
        nullable=False,
        default=NotificationStatusEnum.ACTIVE,
        server_default=NotificationStatusEnum.ACTIVE.value,
        index=True,
    )
    affiliate_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("affiliates.id"), nullable=True, index=True
    )

    user = relationship("ERPUser", back_populates="notifications")
    affiliate = relationship("Affiliate", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(message='{self.message}', type='{self.type}', user_id={self.user_id})>"
