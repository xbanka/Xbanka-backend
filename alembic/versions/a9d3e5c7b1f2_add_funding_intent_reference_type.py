"""add funding_intent reference type to notifications

Revision ID: a9d3e5c7b1f2
Revises: c3d34377f0d5
Create Date: 2026-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a9d3e5c7b1f2'
down_revision: Union[str, Sequence[str], None] = 'c3d34377f0d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationreferencetypeenum ADD VALUE IF NOT EXISTS 'FUNDING_INTENT'")


def downgrade() -> None:
    """Downgrade schema.

    Postgres cannot drop a value from an enum, so this is a no-op (same as the
    other reference-type migrations).
    """
    pass
