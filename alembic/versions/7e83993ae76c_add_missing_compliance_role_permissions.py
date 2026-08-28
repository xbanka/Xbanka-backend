"""add missing compliance role permissions

Revision ID: 7e83993ae76c
Revises: c8b4e1f6a9d3
Create Date: 2026-08-28 12:01:28.390385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e83993ae76c'
down_revision: Union[str, Sequence[str], None] = 'c8b4e1f6a9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_NAME = "Compliance"

# (permission_name, is_allowed)
PERMISSION_CHANGES = [
    ("audit:view_logs", True),
    ("staff:suspend_activate", False),
    ("staff:reset_password", False),
]


def upgrade() -> None:
    """Add role_permissions rows the Compliance role is missing.

    Compliance already exists (seeded outside version control) with most of
    its intended permissions; this only inserts the ones it was missing. Uses
    ON CONFLICT DO NOTHING so it's safe to run against a DB that already has
    any of these rows.
    """
    conn = op.get_bind()
    for permission_name, is_allowed in PERMISSION_CHANGES:
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id, is_allowed)
                SELECT r.id, p.id, :is_allowed
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = :permission_name
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {
                "role_name": ROLE_NAME,
                "permission_name": permission_name,
                "is_allowed": is_allowed,
            },
        )


def downgrade() -> None:
    """Remove the role_permissions rows added in upgrade()."""
    conn = op.get_bind()
    for permission_name, _is_allowed in PERMISSION_CHANGES:
        conn.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                USING roles r, permissions p
                WHERE role_permissions.role_id = r.id
                  AND role_permissions.permission_id = p.id
                  AND r.name = :role_name
                  AND p.name = :permission_name
                """
            ),
            {"role_name": ROLE_NAME, "permission_name": permission_name},
        )
