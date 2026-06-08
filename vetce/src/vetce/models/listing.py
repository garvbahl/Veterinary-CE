from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Text, Boolean, Numeric, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vetce.db import Base


class Listing(Base):
    """A single CE opportunity — one course, webinar, or program.

    Identified uniquely by source_url. Re-scraping the same URL updates
    the existing row rather than creating a duplicate.
    """
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ---- Relationships ----
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    duplicate_of: Mapped[int | None] = mapped_column(
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---- Identity ----
    source_url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)

    # ---- Core content ----
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Schedule (for live events) ----
    starts_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ---- Course attributes ----
    format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cost: Mapped[str | None] = mapped_column(String(100), nullable=True)
    race_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    race_program_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    credit_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    presenter: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivery_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    topics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    registration_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # ---- Raw storage (for re-parsing if extraction logic changes) ----
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # ---- Lifecycle ----
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ---- ORM relationships ----
    provider: Mapped["Provider"] = relationship(back_populates="listings")
    source: Mapped["Source"] = relationship(back_populates="listings")