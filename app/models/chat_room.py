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

    assigned_to: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id"), nullable=True
    )
    assigned_staff = relationship("ERPUser", back_populates="assiged_chat_rooms")

    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    chats = relationship(
        "ChatMessage",
        back_populates="chat_room",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
