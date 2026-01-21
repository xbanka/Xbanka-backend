from app.models.base_model import BaseModel
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String

class Role(BaseModel):
    __tablename__ = 'roles'

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", back_populates="role")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
    