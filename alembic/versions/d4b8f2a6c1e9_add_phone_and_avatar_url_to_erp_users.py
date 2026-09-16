"""add phone and avatar_url to erp_users

Revision ID: d4b8f2a6c1e9
Revises: c9e4a1d7f2b3
Create Date: 2026-09-15 14:00:00.000000

Staff can now set their own phone number via PATCH /erp/me and upload a profile
picture via POST /erp/me/avatar. Both nullable, since existing staff have
neither; phone is stored in E.164 form (at most 16 characters) and avatar_url
holds the S3 object path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b8f2a6c1e9'
down_revision: Union[str, Sequence[str], None] = 'c9e4a1d7f2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('erp_users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('erp_users', sa.Column('avatar_url', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('erp_users', 'avatar_url')
    op.drop_column('erp_users', 'phone')
