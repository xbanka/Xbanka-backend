"""add funding intent logs table

Revision ID: d7a2f4c8e1b6
Revises: a3c9e51d7b02
Create Date: 2026-10-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd7a2f4c8e1b6'
down_revision: Union[str, Sequence[str], None] = 'a3c9e51d7b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

funding_intent_action_enum = postgresql.ENUM(
    "COMPLETED",
    "REJECTED",
    name="fundingintentactionenum",
    create_type=False,
)

funding_intent_log_status_enum = postgresql.ENUM(
    "SUCCESS",
    "FAILED",
    name="fundingintentlogstatusenum",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    funding_intent_action_enum.create(op.get_bind(), checkfirst=True)
    funding_intent_log_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'funding_intent_logs',
        sa.Column('staff_id', sa.UUID(), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=False),
        sa.Column('action', funding_intent_action_enum, nullable=False),
        sa.Column('status', funding_intent_log_status_enum, nullable=False, server_default='SUCCESS'),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('bank_reference', sa.String(), nullable=True),
        sa.Column('override_amount', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('funding_account_id', sa.UUID(), nullable=True),
        sa.Column('attachment_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['erp_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_funding_intent_logs_staff_id'), 'funding_intent_logs', ['staff_id'], unique=False)
    op.create_index(op.f('ix_funding_intent_logs_transaction_id'), 'funding_intent_logs', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_funding_intent_logs_action'), 'funding_intent_logs', ['action'], unique=False)
    op.create_index(op.f('ix_funding_intent_logs_status'), 'funding_intent_logs', ['status'], unique=False)
    op.create_index(op.f('ix_funding_intent_logs_bank_reference'), 'funding_intent_logs', ['bank_reference'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_funding_intent_logs_bank_reference'), table_name='funding_intent_logs')
    op.drop_index(op.f('ix_funding_intent_logs_status'), table_name='funding_intent_logs')
    op.drop_index(op.f('ix_funding_intent_logs_action'), table_name='funding_intent_logs')
    op.drop_index(op.f('ix_funding_intent_logs_transaction_id'), table_name='funding_intent_logs')
    op.drop_index(op.f('ix_funding_intent_logs_staff_id'), table_name='funding_intent_logs')
    op.drop_table('funding_intent_logs')

    funding_intent_log_status_enum.drop(op.get_bind(), checkfirst=True)
    funding_intent_action_enum.drop(op.get_bind(), checkfirst=True)
