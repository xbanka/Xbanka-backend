"""add status to notifications table

Revision ID: 4b6e6947f757
Revises: a3f17c9b2e40
Create Date: 2026-08-22 20:45:04.000000

A notification about an actionable reference (currently only rate proposals)
used to have no way to signal that the reference had already been resolved
by someone else. Every reviewer notified about the same proposal would keep
showing an approve/reject prompt even after another reviewer acted on it.

`status` carries that state per notification: ACTIVE means the reference is
still open and the frontend may still prompt an action; RESOLVED means it
was already actioned elsewhere and any action controls should be disabled.
Existing rows default to ACTIVE, which matches their prior (implicit) state.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b6e6947f757'
down_revision: Union[str, Sequence[str], None] = 'a3f17c9b2e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    notification_status_enum = sa.Enum('ACTIVE', 'RESOLVED', name='notificationstatusenum')
    notification_status_enum.create(op.get_bind())

    op.add_column(
        'notifications',
        sa.Column(
            'status',
            notification_status_enum,
            nullable=False,
            server_default='ACTIVE',
        ),
    )
    op.create_index(
        op.f('ix_notifications_status'), 'notifications', ['status'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_column('notifications', 'status')
    sa.Enum(name='notificationstatusenum').drop(op.get_bind())
