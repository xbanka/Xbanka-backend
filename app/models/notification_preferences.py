import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import NotificationCategoryEnum
from app.db.database import Base


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
