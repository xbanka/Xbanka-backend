"""add staff_account reference type to notifications

Revision ID: f3a1c9d2e4b7
Revises: 4b6e6947f757
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1c9d2e4b7'
down_revision: Union[str, Sequence[str], None] = '4b6e6947f757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationreferencetypeenum ADD VALUE IF NOT EXISTS 'STAFF_ACCOUNT'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
