from app.db.database import Base
from app.models.base_model import BaseModel
from sqlalchemy import ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID


class UserPermissions(Base):
    __tablename__ = "user_permissions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey('erp_users.id', ondelete='CASCADE'), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("ERPUser", back_populates="permission_links")
    permission = relationship("Permission", back_populates="user_links")
