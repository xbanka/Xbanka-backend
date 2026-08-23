"""add requested_by_id to rate_change_logs

Revision ID: c8b4e1f6a9d3
Revises: f3a1c9d2e4b7
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8b4e1f6a9d3'
down_revision: Union[str, Sequence[str], None] = 'f3a1c9d2e4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('rate_change_logs', sa.Column('requested_by_id', sa.UUID(), nullable=True))

    # Existing rows predate the requested_by/performed_by split and never
    # recorded a separate requester; performed_by_id is the closest known
    # actor, so backfill with that rather than losing the row to a NOT NULL
    # violation.
    op.execute('UPDATE rate_change_logs SET requested_by_id = performed_by_id')

    op.alter_column('rate_change_logs', 'requested_by_id', nullable=False)
    op.create_index(op.f('ix_rate_change_logs_requested_by_id'), 'rate_change_logs', ['requested_by_id'], unique=False)
    op.create_foreign_key(None, 'rate_change_logs', 'erp_users', ['requested_by_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_rate_change_logs_requested_by_id'), table_name='rate_change_logs')
    op.drop_column('rate_change_logs', 'requested_by_id')
