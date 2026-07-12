"""add presenter_image_url to listings

Revision ID: 87be5c0226da
Revises: ad36d7b28761
Create Date: 2026-07-12 09:34:12.248554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87be5c0226da'
down_revision: Union[str, Sequence[str], None] = 'ad36d7b28761'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listings', sa.Column('presenter_image_url', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('listings', 'presenter_image_url')
