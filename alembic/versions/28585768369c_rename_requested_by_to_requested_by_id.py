"""rename requested_by to requested_by_id

Revision ID: 28585768369c
Revises: efd4ed7c2996
Create Date: 2026-06-29 14:10:58.633856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28585768369c'
down_revision: Union[str, Sequence[str], None] = 'efd4ed7c2996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op

def upgrade():
    op.alter_column(
        "rate_approval_requests",
        "requested_by",
        new_column_name="requested_by_id",
    )

    op.drop_index(
        "ix_rate_approval_requests_requested_by",
        table_name="rate_approval_requests",
    )

    op.create_index(
        "ix_rate_approval_requests_requested_by_id",
        "rate_approval_requests",
        ["requested_by_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_rate_approval_requests_requested_by_id",
        table_name="rate_approval_requests",
    )

    op.alter_column(
        "rate_approval_requests",
        "requested_by_id",
        new_column_name="requested_by",
    )

    op.create_index(
        "ix_rate_approval_requests_requested_by",
        "rate_approval_requests",
        ["requested_by"],
        unique=False,
    )