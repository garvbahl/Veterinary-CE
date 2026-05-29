from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawListing:
    """Structured CE listing produced by a scraper.

    This is the contract every scraper produces. It is intentionally
    free of database concerns — persistence is a separate layer.
    Fields that a source doesn't provide should be left as None, not
    fabricated. Honest absence > fake data.
    """
    source_slug: str             # which scraper produced this (e.g. "vetmedteam")
    source_url: str              # detail-page URL on the provider's site
    title: str
    provider: str

    description: str | None = None
    starts_at: date | None = None
    ends_at: date | None = None
    format: str | None = None             # "live" | "on_demand" | "hybrid"
    cost: str | None = None               # raw text like "Free", "$45", "Member: $0"
    race_approved: bool | None = None
    race_program_number: str | None = None
    credit_hours: float | None = None
    presenter: str | None = None
    audience: str | None = None           # "vets", "techs", "vets and techs"
    delivery_method: str | None = None    # "Interactive Distance", "Non-interactive Distance", etc.
    subject_category: str | None = None   # RACE subject category
    topics: list[str] = field(default_factory=list)
    registration_url: str | None = None   # often differs from source_url