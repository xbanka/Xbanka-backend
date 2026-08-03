"""add reference_type notifications

Revision ID: 281bdc421957
Revises: 0f9a664f6725
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '281bdc421957'
down_revision: Union[str, Sequence[str], None] = '0f9a664f6725'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    reference_type_enum = sa.Enum(
        'payout', 'rate_proposal', name='notificationreferencetypeenum'
    )
    reference_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'notifications',
        sa.Column(
            'reference_type',
            reference_type_enum,
            nullable=False,
            server_default='payout',
        ),
    )
    op.alter_column('notifications', 'reference_type', server_default=None)
    op.create_index(
        op.f('ix_notifications_reference_type'), 'notifications', ['reference_type'], unique=False
    )
    op.alter_column('notifications', 'amount', existing_type=sa.DECIMAL(12, 2), nullable=True)
    op.alter_column(
        'notifications', 'method',
        existing_type=sa.Enum('bank_transfer', 'mobile_money', name='payoutmethodenum'),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'notifications', 'method',
        existing_type=sa.Enum('bank_transfer', 'mobile_money', name='payoutmethodenum'),
        nullable=False,
    )
    op.alter_column('notifications', 'amount', existing_type=sa.DECIMAL(12, 2), nullable=False)
    op.drop_index(op.f('ix_notifications_reference_type'), table_name='notifications')
    op.drop_column('notifications', 'reference_type')
    sa.Enum(name='notificationreferencetypeenum').drop(op.get_bind(), checkfirst=True)
