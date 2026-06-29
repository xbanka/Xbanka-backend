from sqlalchemy import ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import Dict, Any, List

from app.core.enums import RateApprovalRequestTypeEnum, RatesApprovalStatusEnum
from app.models.base_model import BaseModel


class RateApprovalRequest(BaseModel):
    __tablename__ = "rate_approval_requests"

    type: Mapped[RateApprovalRequestTypeEnum] = mapped_column(
        Enum(RateApprovalRequestTypeEnum),
        nullable=False, 
        index=True
    )
    payload: Mapped[Dict[str, Any] | List[Dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False
    )
    requested_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id"), 
        nullable=False, index=True
    )
    requested_by = relationship(
        "ERPUser", 
        back_populates="rate_requests"
    )
    status: Mapped[RatesApprovalStatusEnum] = mapped_column(
        Enum(RatesApprovalStatusEnum), 
        default=RatesApprovalStatusEnum.PENDING, 
        nullable=False, index=True
    )
    

    def __repr__(self):
        return f"<RateApprovalRequest(type='{self.type}', payload='{self.payload}', requested_by='{self.requested_by}')>"
