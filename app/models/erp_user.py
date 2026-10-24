import uuid
import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel

# Excludes visually ambiguous characters (0/O, 1/I). Statistically unique
# (33^5 ≈ 39M combinations); actual uniqueness is enforced by the DB index.
# Callers that need a DB-verified-unique code should use
# app.services.erp_user.generate_unique_staff_code instead of relying on
# this default.
STAFF_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _default_staff_code() -> str:
    return "ST-" + "".join(secrets.choice(STAFF_CODE_ALPHABET) for _ in range(5))


class ERPUser(BaseModel):
    __tablename__ = "erp_users"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    staff_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True, default=_default_staff_code
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    # E.164 (e.g. +2348031234567); normalised by app.utils.validators.normalize_phone
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # S3 object path of the profile picture, e.g. "avatars/<id>_<hex>.png"
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Fernet-encrypted TOTP secret. Set at /2fa/setup but only enforced at login
    # once totp_enabled flips true (after the first code is confirmed).
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa_false()
    )
    # Last accepted 30s time step; a code is rejected unless its step is newer,
    # so a code can't be replayed inside its validity window.
    totp_last_used_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mfa_failed_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    mfa_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovery_codes = relationship(
        "ERPRecoveryCode",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id"), nullable=False, index=True
    )
    role = relationship("Role", back_populates="users")

    # chat_rooms = relationship("ChatRoom", back_populates="customer")

    permission_links = relationship(
        "UserPermissions",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="permissions",
    )
    permissions = relationship(
        "Permission",
        secondary="user_permissions",
        back_populates="users",
        viewonly=True,
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Both absent until the staff member changes something; see the models for
    # why a missing row means "enabled".
    notification_settings = relationship(
        "NotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_preferences = relationship(
        "NotificationPreference",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    rate_requests = relationship(
        "RateApprovalRequest",
        back_populates="requested_by",
    )

    rate_changes_requested = relationship(
        "RateChangeLog",
        foreign_keys="RateChangeLog.requested_by_id",
        back_populates="requested_by",
    )

    rate_changes_performed = relationship(
        "RateChangeLog",
        foreign_keys="RateChangeLog.performed_by_id",
        back_populates="performed_by",
    )

    role_changes = relationship(
        "RoleChangeLog",
        foreign_keys="RoleChangeLog.staff_id",
        back_populates="staff",
    )

    role_changes_requested = relationship(
        "RoleChangeLog",
        foreign_keys="RoleChangeLog.requested_by_id",
        back_populates="requested_by",
    )

    login_attempts = relationship(
        "LoginLog",
        back_populates="user",
    )

    def __repr__(self):
        return f"<ERPUser(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}')>"
