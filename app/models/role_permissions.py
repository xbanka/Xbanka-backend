from sqlalchemy import Boolean, Column, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class RolePermissions(Base):
    __tablename__ = "role_permissions"

    role_id = Column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    is_allowed = Column(Boolean, default=True, nullable=True)

    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")
