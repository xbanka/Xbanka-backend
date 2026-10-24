import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class ERPRecoveryCode(BaseModel):
    """One single-use 2FA backup code. Only the bcrypt hash is stored, so the
    plaintext codes exist once, in the response that generates them."""

    __tablename__ = "erp_recovery_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("erp_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user = relationship("ERPUser", back_populates="recovery_codes")

    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
