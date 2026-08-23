from sqlalchemy import ForeignKey, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import Dict, Any, List, Optional

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

    requested_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id"),
        nullable=False, index=True
    )
    requested_by = relationship(
        "ERPUser",
        foreign_keys=[requested_by_id],
        back_populates="rate_changes_requested"
    )

    performed_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("erp_users.id"),
        nullable=False, index=True
    )
    performed_by = relationship(
        "ERPUser",
        foreign_keys=[performed_by_id],
        back_populates="rate_changes_performed"
    )

    status: Mapped[RatesApprovalStatusEnum] = mapped_column(
        Enum(RatesApprovalStatusEnum),
        default=RatesApprovalStatusEnum.APPROVED,
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
        return f"<RateChangeLog(type='{self.type}', payload='{self.payload}', performed_by='{self.performed_by}')>"
