"""add staff_code to erp_users

Revision ID: a2d9c7f14b83
Revises: 7e83993ae76c
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2d9c7f14b83'
down_revision: Union[str, Sequence[str], None] = '7e83993ae76c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('erp_users', sa.Column('staff_code', sa.String(length=20), nullable=True))

    # Backfill existing rows with a unique short code, excluding visually
    # ambiguous characters (0/O, 1/I) to match the app-side generator.
    op.execute(
        """
        DO $$
        DECLARE
            alphabet text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
            row_id uuid;
            new_code text;
        BEGIN
            FOR row_id IN SELECT id FROM erp_users WHERE staff_code IS NULL LOOP
                LOOP
                    new_code := 'ST-' || (
                        SELECT string_agg(substr(alphabet, (floor(random() * length(alphabet)) + 1)::int, 1), '')
                        FROM generate_series(1, 5)
                    );
                    EXIT WHEN NOT EXISTS (SELECT 1 FROM erp_users WHERE staff_code = new_code);
                END LOOP;
                UPDATE erp_users SET staff_code = new_code WHERE id = row_id;
            END LOOP;
        END $$;
        """
    )

    op.alter_column('erp_users', 'staff_code', existing_type=sa.String(length=20), nullable=False)
    op.create_index(op.f('ix_erp_users_staff_code'), 'erp_users', ['staff_code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_erp_users_staff_code'), table_name='erp_users')
    op.drop_column('erp_users', 'staff_code')
