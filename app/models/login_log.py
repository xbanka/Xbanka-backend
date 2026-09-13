import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import LoginStatusEnum
from app.models.base_model import BaseModel


class LoginLog(BaseModel):
    __tablename__ = "login_logs"

    attempted_email: Mapped[str] = mapped_column(String, nullable=False, index=True)

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("erp_users.id"), nullable=True, index=True
    )
    user = relationship("ERPUser", back_populates="login_attempts")

    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[LoginStatusEnum] = mapped_column(
        Enum(LoginStatusEnum), nullable=False, index=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __repr__(self):
        return f"<LoginLog(attempted_email='{self.attempted_email}', status='{self.status}')>"
