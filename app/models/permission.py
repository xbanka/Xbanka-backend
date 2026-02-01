from sqlalchemy import String
from app.models.base_model import BaseModel
from sqlalchemy.orm import mapped_column, Mapped, relationship

class Permission(BaseModel):
    __tablename__ = 'permissions'

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")
    role_links = relationship("RolePermissions", back_populates="permission", cascade="all, delete-orphan", passive_deletes=True)

    user_links = relationship("UserPermissions", back_populates="permission")
    users = relationship("ERPUser", secondary="user_permissions", back_populates="permissions", viewonly=True)

    def __repr__(self):
        return f"<Permission(name='{self.name}')>"