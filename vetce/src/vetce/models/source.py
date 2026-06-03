from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vetce.db import Base


class Source(Base):
    """A channel through which CE listings are ingested.

    Each scraper is a source. Manual entry is a source. An RSS feed is a source.
    Sources belong to a provider. One provider can have multiple sources.
    """
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # "scraper" | "manual" | "rss" | "partner"
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    provider: Mapped["Provider"] = relationship(back_populates="sources")
    listings: Mapped[list["Listing"]] = relationship(back_populates="source")
    runs: Mapped[list["ScrapeRun"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )
    cron_expression: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )