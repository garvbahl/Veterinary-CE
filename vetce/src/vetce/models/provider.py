from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vetce.db import Base


class Provider(Base):
    """A CE provider (e.g., VetMedTeam, AAHA).

    One provider can have many sources and many listings.
    """
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Reverse relationships (filled in once Source and Listing models exist)
    sources: Mapped[list["Source"]] = relationship(back_populates="provider")
    listings: Mapped[list["Listing"]] = relationship(back_populates="provider")