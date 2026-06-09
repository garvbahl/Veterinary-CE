"""add normalized_title column to listings

Revision ID: def254696427
Revises: 4edd9e17054b
Create Date: 2026-06-08 18:14:27.002665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'def254696427'
down_revision: Union[str, Sequence[str], None] = '4edd9e17054b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the column (nullable so the add itself can't fail on existing data).
    op.add_column(
        "listings",
        sa.Column("normalized_title", sa.String(length=500), nullable=True),
    )
    op.create_index(
        op.f("ix_listings_normalized_title"),
        "listings",
        ["normalized_title"],
        unique=False,
    )

    # 2. Backfill existing rows using the canonical Python normalizer.
    from sqlalchemy.orm import Session

    from vetce.pipeline.dedup import normalize_title

    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        rows = session.execute(sa.text("SELECT id, title FROM listings")).all()
        for row in rows:
            session.execute(
                sa.text("UPDATE listings SET normalized_title = :n WHERE id = :id"),
                {"n": normalize_title(row.title), "id": row.id},
            )
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    op.drop_index(op.f("ix_listings_normalized_title"), table_name="listings")
    op.drop_column("listings", "normalized_title")
