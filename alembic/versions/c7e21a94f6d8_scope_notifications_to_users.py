"""scope notifications to users, add rates permissions

Revision ID: c7e21a94f6d8
Revises: bee97b3453f4
Create Date: 2026-08-07 09:12:44.108225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e21a94f6d8'
down_revision: Union[str, Sequence[str], None] = 'bee97b3453f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO permissions (id, name, category, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'rates:propose_changes', 'Rates', now(), now()),
            (gen_random_uuid(), 'rates:approve_changes', 'Rates', now(), now())
        ON CONFLICT (name) DO NOTHING
        """
    )

    # rates:propose_changes goes to Operations. rates:approve_changes is granted
    # to no role on purpose — Super Admin resolves to every permission in code
    # (see ERPService.get_role_permissions), so it needs no row here.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, is_allowed)
        SELECT r.id, p.id, true
        FROM roles r, permissions p
        WHERE r.name = 'Operations' AND p.name = 'rates:propose_changes'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )

    op.add_column('notifications', sa.Column('user_id', sa.UUID(), nullable=True))

    # Existing notifications are global. Fan each one out to every ERP user so
    # nobody loses history, carrying the old is_read forward. The SELECT reads
    # the statement's snapshot, so it never sees the rows this INSERT creates.
    op.execute(
        """
        INSERT INTO notifications (
            id, user_id, message, type, is_read, read_at, amount, method,
            reference_type, reference_id, affiliate_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), u.id, n.message, n.type, n.is_read, n.read_at,
            n.amount, n.method, n.reference_type, n.reference_id,
            n.affiliate_id, n.created_at, n.updated_at
        FROM notifications n
        CROSS JOIN erp_users u
        WHERE n.user_id IS NULL
        """
    )
    op.execute("DELETE FROM notifications WHERE user_id IS NULL")

    op.alter_column('notifications', 'user_id', nullable=False)
    op.create_foreign_key(
        'fk_notifications_user_id_erp_users',
        'notifications',
        'erp_users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index(
        'ix_notifications_user_read', 'notifications', ['user_id', 'is_read']
    )


def downgrade() -> None:
    """Downgrade schema.

    Lossy by nature: once notifications are per-user there is no record of which
    rows came from the same original event, so this collapses to one row per
    distinct (message, reference_type, reference_id, affiliate_id, created_at)
    and keeps that row's read state. Two genuinely separate events that agree on
    all five columns merge into one.
    """
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_constraint(
        'fk_notifications_user_id_erp_users', 'notifications', type_='foreignkey'
    )

    # collapse the per-user copies back down to one row per original event
    op.execute(
        """
        DELETE FROM notifications a
        USING notifications b
        WHERE a.ctid > b.ctid
          AND a.message IS NOT DISTINCT FROM b.message
          AND a.reference_type IS NOT DISTINCT FROM b.reference_type
          AND a.reference_id IS NOT DISTINCT FROM b.reference_id
          AND a.affiliate_id IS NOT DISTINCT FROM b.affiliate_id
          AND a.created_at IS NOT DISTINCT FROM b.created_at
        """
    )
    op.drop_column('notifications', 'user_id')

    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE name IN ('rates:propose_changes', 'rates:approve_changes')
        )
        """
    )
    op.execute(
        """
        DELETE FROM permissions
        WHERE name IN ('rates:propose_changes', 'rates:approve_changes')
        """
    )
