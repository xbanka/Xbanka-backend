"""Convert notification reference types to uppercase

Revision ID: bee97b3453f4
Revises: 281bdc421957
Create Date: 2026-08-05 06:39:26.913190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bee97b3453f4'
down_revision: Union[str, Sequence[str], None] = '281bdc421957'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('ALTER TYPE notificationreferencetypeenum RENAME TO notificationreferencetypeenum_old')
    sa.Enum('PAYOUT', 'RATE_PROPOSAL', name='notificationreferencetypeenum').create(op.get_bind())
    op.execute(
        'ALTER TABLE notifications ALTER COLUMN reference_type TYPE notificationreferencetypeenum '
        'USING UPPER(reference_type::text)::notificationreferencetypeenum'
    )
    op.execute('DROP TYPE notificationreferencetypeenum_old')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TYPE notificationreferencetypeenum RENAME TO notificationreferencetypeenum_old')
    sa.Enum('payout', 'rate_proposal', name='notificationreferencetypeenum').create(op.get_bind())
    op.execute(
        'ALTER TABLE notifications ALTER COLUMN reference_type TYPE notificationreferencetypeenum '
        'USING LOWER(reference_type::text)::notificationreferencetypeenum'
    )
    op.execute('DROP TYPE notificationreferencetypeenum_old')
