import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import NotificationCategoryEnum
from app.db.database import Base


# What a staff member gets before they change anything, per the settings
# design: everything in-app, but email only where it is worth interrupting
# someone's inbox. Editing this map moves everyone who has no row for that
# category; anyone who has already chosen keeps their choice.
DEFAULT_NOTIFICATION_PREFERENCES: dict[NotificationCategoryEnum, dict[str, bool]] = {
    NotificationCategoryEnum.TRANSACTION_ACTIVITY: {"in_app": True, "email": False},
    NotificationCategoryEnum.APPROVAL_REQUESTS: {"in_app": True, "email": False},
    NotificationCategoryEnum.ROLE_PERMISSION_CHANGES: {"in_app": True, "email": False},
    NotificationCategoryEnum.RATE_MANAGEMENT: {"in_app": True, "email": False},
    NotificationCategoryEnum.KYC_VERIFICATION: {"in_app": True, "email": False},
    NotificationCategoryEnum.SUPPORT_ACTIVITY: {"in_app": True, "email": True},
    NotificationCategoryEnum.SYSTEM_SECURITY: {"in_app": True, "email": True},
}


class NotificationPreference(Base):
    """One staff member's toggles for one notification category.

    Rows are written only for categories they actually change - an absent row
    means both channels are on, the same convention user_permissions uses for
    overrides.
    """

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("erp_users.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[NotificationCategoryEnum] = mapped_column(
        Enum(NotificationCategoryEnum), primary_key=True
    )

    in_app: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    user = relationship("ERPUser", back_populates="notification_preferences")

    def __repr__(self):
        return (
            f"<NotificationPreference(user_id={self.user_id}, "
            f"category='{self.category}', in_app={self.in_app}, email={self.email})>"
        )
