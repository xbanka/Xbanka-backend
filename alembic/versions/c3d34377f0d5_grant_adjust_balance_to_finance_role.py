"""grant finance:adjust_balance to the Finance role

Revision ID: c3d34377f0d5
Revises: d7a2f4c8e1b6
Create Date: 2026-11-10 00:00:00.000000

Finance staff need finance:adjust_balance, which guards the balance
adjustment routes in app/api/v1/routes/transaction.py. The permission row
already exists (seeded by 51b03fe4c709); only the Finance grant was missing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d34377f0d5"
down_revision: Union[str, Sequence[str], None] = "d7a2f4c8e1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_NAME = "Finance"
PERMISSION_NAME = "finance:adjust_balance"


def upgrade() -> None:
    """Insert the role_permissions row. ON CONFLICT DO NOTHING makes this a
    no-op on a database that already has the grant."""
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = :role_name AND p.name = :permission_name
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ),
        {"role_name": ROLE_NAME, "permission_name": PERMISSION_NAME},
    )


def downgrade() -> None:
    """Remove the grant. Per-staff overrides in user_permissions are untouched."""
    op.get_bind().execute(
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
        {"role_name": ROLE_NAME, "permission_name": PERMISSION_NAME},
    )
