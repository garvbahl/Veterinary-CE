"""SQLAlchemy model for scrape_runs — one row per scraper invocation."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vetce.db import Base

if TYPE_CHECKING:
    from vetce.models.source import Source
    from vetce.models.listing import Listing
    from vetce.models.scrape_run import ScrapeRun




class ScrapeRun(Base):
    """Records one invocation of one scraper.

    Lifecycle:
      1. Created at scrape start with status='running', finished_at=NULL.
      2. Updated at scrape end with status='success'/'failed'/'partial',
         finished_at=now(), and the count columns populated.

    If the process crashes between step 1 and step 2, the row stays in
    'running' state — this is intentional and lets us detect zombie runs.
    """

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 'running' | 'success' | 'failed' | 'partial'
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    listings_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    listings_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    listings_errored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="runs")

    def __repr__(self) -> str:
        return (
            f"<ScrapeRun id={self.id} source_id={self.source_id} "
            f"status={self.status} started_at={self.started_at}>"
        )