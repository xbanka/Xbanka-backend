from app.db.database import Base
from app.models.base_model import BaseModel
from sqlalchemy import ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID


class UserPermissions(Base):
    __tablename__ = "user_permissions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey('permissions.id'), primary_key=True)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user = relationship("ERPUser", back_populates="permission_links")
    permission = relationship("Permission", back_populates="user_links")
