"""add configuration snapshots to rate approval requests and rate change logs

Revision ID: a1f3c9d7b2e4
Revises: 4441132d04cc
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1f3c9d7b2e4'
down_revision: Union[str, Sequence[str], None] = '4441132d04cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows have no way to know what "previous"/"new" configuration
    # was at the time they were created (that data was never persisted), so
    # they can't be backfilled. Wipe both tables before adding NOT NULL
    # snapshot columns.
    op.execute('TRUNCATE TABLE rate_change_logs, rate_approval_requests')

    for table in ('rate_approval_requests', 'rate_change_logs'):
        op.add_column(table, sa.Column('previous_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        op.add_column(table, sa.Column('new_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        op.add_column(table, sa.Column('target_label', sa.String(), nullable=False))
        op.add_column(table, sa.Column('target_currency', sa.String(), nullable=True))
        op.add_column(table, sa.Column('affected_assets', sa.Integer(), nullable=False, server_default='1'))
        op.alter_column(table, 'affected_assets', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('rate_approval_requests', 'rate_change_logs'):
        op.drop_column(table, 'affected_assets')
        op.drop_column(table, 'target_currency')
        op.drop_column(table, 'target_label')
        op.drop_column(table, 'new_configuration')
        op.drop_column(table, 'previous_configuration')
