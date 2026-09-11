"""drop role_permissions.is_allowed

Revision ID: b5d2e8f1c4a7
Revises: a3c3e62bc948
Create Date: 2026-09-11 10:00:00.000000

Roles no longer forbid permissions: any permission can be assigned to any
staff member through a user_permissions override. A role_permissions row now
simply means "this role grants the permission by default", so the flag carries
no information.

Rows with is_allowed = false were the forbidden entries. They are deleted
before the column is dropped - dropping the column alone would silently turn
each of them into a default grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d2e8f1c4a7'
down_revision: Union[str, Sequence[str], None] = 'a3c3e62bc948'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DELETE FROM role_permissions WHERE is_allowed = false")
    op.drop_column('role_permissions', 'is_allowed')


def downgrade() -> None:
    """Downgrade schema.

    Lossy: the forbidden rows deleted by the upgrade are not restored. Every
    remaining row comes back as is_allowed = true, which is what it meant
    before the upgrade.
    """
    op.add_column(
        'role_permissions',
        sa.Column('is_allowed', sa.Boolean(), server_default=sa.true(), nullable=False),
    )
