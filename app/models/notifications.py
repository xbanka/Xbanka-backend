from app.core.enums import NotificationTypeEnum
from app.models.base_model import BaseModel
from sqlalchemy import String, Enum, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

class Notification(BaseModel):
    __tablename__ = 'notifications'

    message: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[NotificationTypeEnum] = mapped_column(Enum(NotificationTypeEnum), nullable=False, default=NotificationTypeEnum.system, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("erp_users.id"), nullable=False, index=True)

    user = relationship("ERPUser", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(message='{self.message}', type='{self.type}', user_id={self.user_id})>"