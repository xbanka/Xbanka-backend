from sqlalchemy import ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import Dict, Any, List

from app.core.enums import RateApprovalRequestTypeEnum, RatesApprovalStatusEnum
from app.models.base_model import BaseModel


class RateChangeLog(BaseModel):
    __tablename__ = "rate_change_logs"

    type: Mapped[RateApprovalRequestTypeEnum] = mapped_column(
        Enum(RateApprovalRequestTypeEnum),
        nullable=False, 
        index=True
    )
    payload: Mapped[Dict[str, Any] | List[Dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False
    )
    target_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        nullable=True, 
        index=True
    )
    performed_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id"), 
        nullable=False, index=True
    )
    performed_by = relationship(
        "ERPUser", 
        back_populates="rate_changes"
    )
    

    def __repr__(self):
        return f"<RateChangeLog(type='{self.type}', payload='{self.payload}', performed_by='{self.performed_by}')>"
