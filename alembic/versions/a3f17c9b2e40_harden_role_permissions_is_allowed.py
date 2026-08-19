"""harden role_permissions.is_allowed against NULLs

Revision ID: a3f17c9b2e40
Revises: c7e21a94f6d8
Create Date: 2026-08-19 09:41:12.663201

`is_allowed` carried only a Python-side default (`default=True`), which the ORM
applies on flush but raw SQL never sees. Rows seeded by hand or by earlier data
migrations therefore landed as NULL, and every consumer filters on
`RolePermissions.is_allowed` — where NULL is falsy. A NULL row is silently a
denial, which is the opposite of the intended default.

In practice this hit Super Admin: all 59 of its rows were NULL, so it resolved
to no permissions at all through the role_permissions path. That is handled in
code now (Super Admin resolves against the whole permissions table), but the
column itself is still able to reintroduce the problem for any other role.

This backfills the NULLs to true — the value the ORM default would have given
them — then adds a server default and a NOT NULL constraint so the state cannot
recur.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f17c9b2e40'
down_revision: Union[str, Sequence[str], None] = 'c7e21a94f6d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill before constraining. true is what `default=True` would have set;
    # these rows were written as grants, and only missed the default because
    # they were inserted outside the ORM.
    op.execute("UPDATE role_permissions SET is_allowed = true WHERE is_allowed IS NULL")

    op.alter_column(
        'role_permissions',
        'is_allowed',
        existing_type=sa.Boolean(),
        server_default=sa.true(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    Lossy: rows that were NULL before the upgrade are indistinguishable from
    rows that were explicitly true, so they stay true rather than reverting to
    NULL. That is the safe direction — it preserves grants rather than silently
    turning them back into denials.
    """
    op.alter_column(
        'role_permissions',
        'is_allowed',
        existing_type=sa.Boolean(),
        server_default=None,
        nullable=True,
    )
