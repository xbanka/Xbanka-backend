from sqlalchemy import ForeignKey, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import Dict, Any, List, Optional

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
    target_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
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
    previous_configuration: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False
    )
    new_configuration: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False
    )
    target_label: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    target_currency: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True
    )
    affected_assets: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )


    def __repr__(self):
        return f"<RateApprovalRequest(type='{self.type}', payload='{self.payload}', requested_by='{self.requested_by}')>"
