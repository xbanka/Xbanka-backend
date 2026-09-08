"""add role change logs and login logs tables

Revision ID: a3c3e62bc948
Revises: a2d9c7f14b83
Create Date: 2026-09-07 13:11:54.862017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3c3e62bc948'
down_revision: Union[str, Sequence[str], None] = 'a2d9c7f14b83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

role_change_status_enum = postgresql.ENUM(
    "PENDING",
    "CONFIRMED",
    name="rolechangestatusenum",
    create_type=False,
)

login_status_enum = postgresql.ENUM(
    "SUCCESS",
    "FAILED",
    name="loginstatusenum",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    role_change_status_enum.create(op.get_bind(), checkfirst=True)
    login_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'role_change_logs',
        sa.Column('staff_id', sa.UUID(), nullable=False),
        sa.Column('requested_by_id', sa.UUID(), nullable=False),
        sa.Column('previous_role', sa.String(), nullable=False),
        sa.Column('new_role', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('pending_permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', role_change_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['erp_users.id'], ),
        sa.ForeignKeyConstraint(['requested_by_id'], ['erp_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_role_change_logs_staff_id'), 'role_change_logs', ['staff_id'], unique=False)
    op.create_index(op.f('ix_role_change_logs_requested_by_id'), 'role_change_logs', ['requested_by_id'], unique=False)
    op.create_index(op.f('ix_role_change_logs_status'), 'role_change_logs', ['status'], unique=False)

    op.create_table(
        'login_logs',
        sa.Column('attempted_email', sa.String(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('status', login_status_enum, nullable=False),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['erp_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_login_logs_attempted_email'), 'login_logs', ['attempted_email'], unique=False)
    op.create_index(op.f('ix_login_logs_user_id'), 'login_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_login_logs_status'), 'login_logs', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_login_logs_status'), table_name='login_logs')
    op.drop_index(op.f('ix_login_logs_user_id'), table_name='login_logs')
    op.drop_index(op.f('ix_login_logs_attempted_email'), table_name='login_logs')
    op.drop_table('login_logs')

    op.drop_index(op.f('ix_role_change_logs_status'), table_name='role_change_logs')
    op.drop_index(op.f('ix_role_change_logs_requested_by_id'), table_name='role_change_logs')
    op.drop_index(op.f('ix_role_change_logs_staff_id'), table_name='role_change_logs')
    op.drop_table('role_change_logs')

    login_status_enum.drop(op.get_bind(), checkfirst=True)
    role_change_status_enum.drop(op.get_bind(), checkfirst=True)
