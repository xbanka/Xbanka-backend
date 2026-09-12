from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from app.models.base_model import BaseModel
from app.models.permission import Permission

SUPER_ADMIN = "Super Admin"


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    users = relationship("ERPUser", back_populates="role")

    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        viewonly=True,
        overlaps="permission_links,permissions",
    )
    permission_links = relationship(
        "RolePermissions",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="permissions",
    )

    @property
    def allowed_permissions(self) -> list[str]:
        """Names of the permissions this role grants by default.
        """
        if self.name == SUPER_ADMIN:
            session = object_session(self)
            if session is None:
                return []
            return list(
                session.scalars(select(Permission.name).order_by(Permission.name))
            )

        return [link.permission.name for link in self.permission_links]

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
