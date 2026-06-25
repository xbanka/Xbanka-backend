from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class ERPUser(BaseModel):
    __tablename__ = "erp_users"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)

    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id"), nullable=False, index=True
    )
    role = relationship("Role", back_populates="users")

    # chat_rooms = relationship("ChatRoom", back_populates="customer")

    permission_links = relationship(
        "UserPermissions",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="permissions",
    )
    permissions = relationship(
        "Permission",
        secondary="user_permissions",
        back_populates="users",
        viewonly=True,
    )

    rate_requests = relationship(
        "RateApprovalRequest",
        back_populates="requested_by",
    )

    def __repr__(self):
        return f"<ERPUser(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}')>"
