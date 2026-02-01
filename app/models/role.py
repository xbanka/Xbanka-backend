from app.models.base_model import BaseModel
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String

class Role(BaseModel):
    __tablename__ = 'roles'

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    users = relationship("ERPUser", back_populates="role")

    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
    permission_links = relationship("RolePermissions", back_populates="role", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
    