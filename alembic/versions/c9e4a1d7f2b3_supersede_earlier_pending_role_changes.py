"""supersede earlier pending role changes

Revision ID: c9e4a1d7f2b3
Revises: b5d2e8f1c4a7
Create Date: 2026-09-11 12:00:00.000000

Proposing a role change now invalidates every earlier pending one for the same
staff member by marking it SUPERSEDED, so its id can no longer be confirmed.

Staff who already have more than one pending change keep only their newest;
the rest are superseded here, matching what the new code would have done.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c9e4a1d7f2b3'
down_revision: Union[str, Sequence[str], None] = 'b5d2e8f1c4a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres refuses to use an enum value in the transaction that added it,
    # so commit the new value before the backfill below.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE rolechangestatusenum ADD VALUE IF NOT EXISTS 'SUPERSEDED'")

    op.execute(
        """
        UPDATE role_change_logs AS rc
        SET status = 'SUPERSEDED'
        WHERE rc.status = 'PENDING'
          AND EXISTS (
              SELECT 1 FROM role_change_logs AS newer
              WHERE newer.staff_id = rc.staff_id
                AND newer.status = 'PENDING'
                AND newer.created_at > rc.created_at
          )
        """
    )


def downgrade() -> None:
    """Downgrade schema.

    No-op: Postgres can't drop an enum value, and turning SUPERSEDED rows back
    into PENDING would make stale requests confirmable again.
    """
    pass
