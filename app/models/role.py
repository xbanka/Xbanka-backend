from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    users = relationship("ERPUser", back_populates="role")

    permissions = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )
    permission_links = relationship(
        "RolePermissions",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="permissions",
    )

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
