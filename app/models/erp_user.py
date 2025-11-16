from app.core.enums import UserRoleEnum
from app.models.base_model import BaseModel
from sqlalchemy import String, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

class ERPUser(BaseModel):
    __tablename__ = 'erp_users'

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRoleEnum] = mapped_column(Enum(UserRoleEnum), default=UserRoleEnum.customer_support, nullable=False, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)

    notifications = relationship("Notification", back_populates="user")

    def __repr__(self):
        return f"<ERPUser(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}')>"