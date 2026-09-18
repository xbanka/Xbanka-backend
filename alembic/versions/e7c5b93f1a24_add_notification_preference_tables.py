"""add notification preference tables

Revision ID: e7c5b93f1a24
Revises: d4b8f2a6c1e9
Create Date: 2026-09-18 10:00:00.000000

Storage for the Settings - Notifications page: two channel switches per staff
member (notification_settings) and per-category toggles
(notification_preferences).

Neither table is backfilled. A missing row means the channel or category is on,
so existing staff keep receiving exactly what they receive today until they
change something.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e7c5b93f1a24'
down_revision: Union[str, Sequence[str], None] = 'd4b8f2a6c1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


notification_category_enum = postgresql.ENUM(
    "TRANSACTION_ACTIVITY",
    "APPROVAL_REQUESTS",
    "ROLE_PERMISSION_CHANGES",
    "RATE_MANAGEMENT",
    "KYC_VERIFICATION",
    "SUPPORT_ACTIVITY",
    "SYSTEM_SECURITY",
    name="notificationcategoryenum",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    notification_category_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'notification_settings',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('in_app_enabled', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['erp_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.create_table(
        'notification_preferences',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('category', notification_category_enum, nullable=False),
        sa.Column('in_app', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('email', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['erp_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'category'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('notification_preferences')
    op.drop_table('notification_settings')
    notification_category_enum.drop(op.get_bind(), checkfirst=True)
