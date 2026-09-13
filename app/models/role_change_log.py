import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RoleChangeStatusEnum
from app.models.base_model import BaseModel


class RoleChangeLog(BaseModel):
    __tablename__ = "role_change_logs"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("erp_users.id"), nullable=False, index=True
    )
    staff = relationship(
        "ERPUser", foreign_keys=[staff_id], back_populates="role_changes"
    )

    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("erp_users.id"), nullable=False, index=True
    )
    requested_by = relationship(
        "ERPUser",
        foreign_keys=[requested_by_id],
        back_populates="role_changes_requested",
    )

    previous_role: Mapped[str] = mapped_column(String, nullable=False)
    new_role: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Snapshot of `selected_permissions` when a permission change is bundled
    # with the role change in the same request - applied together on confirm.
    pending_permissions: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )

    status: Mapped[RoleChangeStatusEnum] = mapped_column(
        Enum(RoleChangeStatusEnum),
        nullable=False,
        default=RoleChangeStatusEnum.PENDING,
        server_default=RoleChangeStatusEnum.PENDING.value,
        index=True,
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self):
        return f"<RoleChangeLog(staff_id={self.staff_id}, {self.previous_role} -> {self.new_role}, status='{self.status}')>"
