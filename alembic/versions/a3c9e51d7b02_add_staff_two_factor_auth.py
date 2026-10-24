"""add staff two-factor auth

Revision ID: a3c9e51d7b02
Revises: 51b03fe4c709
Create Date: 2026-10-23 10:00:00.000000

TOTP columns on erp_users plus a table of hashed single-use recovery codes.
Existing staff get totp_enabled = false, so their login is unchanged until they
enroll.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c9e51d7b02'
down_revision: Union[str, Sequence[str], None] = '51b03fe4c709'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('erp_users', sa.Column('totp_secret', sa.String(length=255), nullable=True))
    op.add_column(
        'erp_users',
        sa.Column('totp_enabled', sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column('erp_users', sa.Column('totp_last_used_step', sa.Integer(), nullable=True))
    op.add_column(
        'erp_users',
        sa.Column('mfa_failed_attempts', sa.Integer(), server_default='0', nullable=False),
    )
    op.add_column(
        'erp_users', sa.Column('mfa_locked_until', sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        'erp_recovery_codes',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['erp_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
    )
    op.create_index(
        op.f('ix_erp_recovery_codes_user_id'), 'erp_recovery_codes', ['user_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_erp_recovery_codes_user_id'), table_name='erp_recovery_codes')
    op.drop_table('erp_recovery_codes')
    op.drop_column('erp_users', 'mfa_locked_until')
    op.drop_column('erp_users', 'mfa_failed_attempts')
    op.drop_column('erp_users', 'totp_last_used_step')
    op.drop_column('erp_users', 'totp_enabled')
    op.drop_column('erp_users', 'totp_secret')
