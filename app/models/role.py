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
        """Names of the permissions this role grants.

        Super Admin is resolved against the whole permissions table instead of
        its own role_permissions rows. It holds every permission with no
        exceptions, so any permission added after it was seeded would otherwise
        be invisible to it — and its existing rows carry is_allowed = NULL,
        which the is_allowed filter below would drop anyway. This matches how
        ERPService.get_role_permissions already resolves the role.

        Every other role is the subset of its links explicitly flagged allowed.
        """
        if self.name == SUPER_ADMIN:
            session = object_session(self)
            if session is None:
                return []
            return list(
                session.scalars(select(Permission.name).order_by(Permission.name))
            )

        return [link.permission.name for link in self.permission_links if link.is_allowed]

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
