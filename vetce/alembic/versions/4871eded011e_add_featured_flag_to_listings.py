"""add featured flag to listings

Revision ID: 4871eded011e
Revises: 87be5c0226da
Create Date: 2026-08-06 09:30:00.000000

Adds a `featured` boolean and an optional `featured_rank` integer so specific
listings (for example a partner's webinar getting preferred placement) can be
pinned to the top of the homepage. featured_rank orders featured items when
more than one is set; lower numbers surface first, NULLs sort last.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4871eded011e'
down_revision: Union[str, Sequence[str], None] = '87be5c0226da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'listings',
        sa.Column(
            'featured',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        'listings',
        sa.Column('featured_rank', sa.Integer(), nullable=True),
    )
    # Partial index: we only ever query WHERE featured IS TRUE, so index just
    # those rows. Keeps the index tiny and the homepage lookup fast.
    op.create_index(
        'ix_listings_featured',
        'listings',
        ['featured'],
        unique=False,
        postgresql_where=sa.text('featured'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_listings_featured', table_name='listings')
    op.drop_column('listings', 'featured_rank')
    op.drop_column('listings', 'featured')