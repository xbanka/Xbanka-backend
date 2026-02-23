from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel

Base = declarative_base()


class ChatRoom(BaseModel):
    __tablename__ = "chat_rooms"

    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"))
    customer = relationship("Customer", back_populates="chat_rooms")

    support_agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id"), nullable=True
    )
    support_agent = relationship("ERPUser", back_populates="chat_rooms")

    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
