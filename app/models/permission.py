from sqlalchemy import ForeignKey, String
from app.models.base_model import BaseModel
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID 

class Permission(BaseModel):
    __tablename__ = 'permissions'

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    role_id: Mapped[UUID] = mapped_column(ForeignKey('roles.id'), nullable=False)
    role = relationship("Role", back_populates="permissions")

    user_links = relationship("UserPermissions", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Permission(name='{self.name}', description='{self.description}', role_id='{self.role_id}')>"