from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class RolePermissions(Base):
    """A permission a role grants by default. Roles never forbid a permission:
    anything without a row here can still be assigned per user."""

    __tablename__ = "role_permissions"

    role_id = Column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")
