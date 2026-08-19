from sqlalchemy import Boolean, Column, ForeignKey, true
from sqlalchemy.orm import relationship

from app.db.database import Base


class RolePermissions(Base):
    __tablename__ = "role_permissions"

    role_id = Column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    # server_default, not just the Python-side default: rows inserted by raw SQL
    # (data migrations, manual seeding) bypass the ORM default and used to land
    # as NULL, which every is_allowed filter then treated as "denied". NOT NULL
    # makes that failure mode impossible rather than merely unlikely.
    is_allowed = Column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")
