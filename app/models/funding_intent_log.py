import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FundingIntentActionEnum, FundingIntentLogStatusEnum
from app.models.base_model import BaseModel


class FundingIntentLog(BaseModel):
    """One row per complete/reject attempt on a customer's funding intent.

    The intents themselves live in the core backend, so `transaction_id` is a
    plain UUID with no foreign key. `staff` is the authenticated user who acted,
    taken from the token rather than the `creditedBy`/`rejectedBy` the client sends.
    """

    __tablename__ = "funding_intent_logs"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("erp_users.id"), nullable=False, index=True
    )
    staff = relationship("ERPUser", foreign_keys=[staff_id])

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    action: Mapped[FundingIntentActionEnum] = mapped_column(
        Enum(FundingIntentActionEnum), nullable=False, index=True
    )

    # FAILED rows are attempts the core backend refused (e.g. already settled by
    # someone else); `failure_reason` carries its status code and message.
    status: Mapped[FundingIntentLogStatusEnum] = mapped_column(
        Enum(FundingIntentLogStatusEnum),
        nullable=False,
        default=FundingIntentLogStatusEnum.SUCCESS,
        server_default=FundingIntentLogStatusEnum.SUCCESS.value,
        index=True,
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # COMPLETED only
    bank_reference: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    # Set only when staff credited a different figure than the customer declared.
    override_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    funding_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    attachment_urls: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    # The override reason when completed with a different amount, or the
    # rejection reason when rejected.
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __repr__(self):
        return f"<FundingIntentLog(transaction_id={self.transaction_id}, action='{self.action}', staff_id={self.staff_id})>"
