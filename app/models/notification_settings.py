import uuid

from sqlalchemy import Boolean, ForeignKey, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# Both channels are on until the staff member says otherwise; the per-category
# defaults in notification_preferences decide what actually reaches them.
DEFAULT_CHANNEL_SETTINGS: dict[str, bool] = {"in_app": True, "email": True}


class NotificationSettings(Base):
    """A staff member's two channel switches.

    A row exists only once they change something: no row means both channels
    are on, so existing staff need no backfill.
    """

    __tablename__ = "notification_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("erp_users.id", ondelete="CASCADE"), primary_key=True
    )

    in_app_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    user = relationship("ERPUser", back_populates="notification_settings")

    def __repr__(self):
        return (
            f"<NotificationSettings(user_id={self.user_id}, "
            f"in_app={self.in_app_enabled}, email={self.email_enabled})>"
        )
