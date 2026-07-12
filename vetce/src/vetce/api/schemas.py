"""Pydantic response schemas for the vetce API.

These are the public-facing shapes of the data we return. They are DELIBERATELY
distinct from the SQLAlchemy models in vetce.models — the database and the API
contract are allowed to diverge.

Conversion from ORM model to Pydantic schema happens via the `from_listing()`
(etc.) factory methods at the bottom of each schema. Endpoints fetch ORM
objects, then call these factories, then return the Pydantic objects.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from vetce.models import Listing, Provider, ScrapeRun, Source


# ============================================================
# Listing
# ============================================================

class ListingOut(BaseModel):
    """Public shape of a single CE listing."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    provider: str = Field(description="Display name of the provider, e.g. 'NAVTA'.")
    source: str = Field(description="Slug of the source that produced this listing.")
    description: Optional[str] = None
    source_url: str
    registration_url: Optional[str] = None

    starts_at: Optional[date] = None
    ends_at: Optional[date] = None

    format: Optional[str] = Field(
        default=None,
        description="One of 'live', 'on_demand', 'hybrid'.",
    )
    cost: Optional[str] = None
    race_approved: Optional[bool] = None
    race_program_number: Optional[str] = None
    credit_hours: Optional[float] = None
    presenter: Optional[str] = None
    presenter_image_url: Optional[str] = None
    audience: Optional[str] = None
    delivery_method: Optional[str] = None
    subject_category: Optional[str] = None

    @classmethod
    def from_listing(cls, listing: "Listing") -> "ListingOut":
        """Build a ListingOut from an ORM Listing.

        Requires that `listing.provider` and `listing.source` are loaded
        (use joinedload or selectinload at the query level).
        """
        return cls(
            id=listing.id,
            title=listing.title,
            provider=listing.provider.name if listing.provider else "",
            source=listing.source.slug if listing.source else "",
            description=listing.description,
            source_url=listing.source_url,
            registration_url=listing.registration_url,
            starts_at=listing.starts_at,
            ends_at=listing.ends_at,
            format=listing.format,
            cost=listing.cost,
            race_approved=listing.race_approved,
            race_program_number=listing.race_program_number,
            credit_hours=float(listing.credit_hours) if listing.credit_hours is not None else None,
            presenter=listing.presenter,
            audience=listing.audience,
            delivery_method=listing.delivery_method,
            subject_category=listing.subject_category,
        )


class ListingsPage(BaseModel):
    """A page of listings, for paginated endpoints (used in Step 5.4)."""
    items: list[ListingOut]
    total: int
    limit: int
    offset: int


# ============================================================
# Provider
# ============================================================

class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    website: Optional[str] = None
    listing_count: Optional[int] = None  # populated by some endpoints, not others

    @classmethod
    def from_provider(
        cls,
        provider: "Provider",
        listing_count: int | None = None,
    ) -> "ProviderOut":
        return cls(
            id=provider.id,
            slug=provider.slug,
            name=provider.name,
            website=provider.website,
            listing_count=listing_count,
        )


# ============================================================
# Source
# ============================================================

class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    kind: str
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    provider_slug: str
    listing_count: Optional[int] = None

    @classmethod
    def from_source(
        cls,
        source: "Source",
        listing_count: int | None = None,
    ) -> "SourceOut":
        return cls(
            id=source.id,
            slug=source.slug,
            kind=source.kind,
            description=source.description,
            cron_expression=source.cron_expression,
            provider_slug=source.provider.slug if source.provider else "",
            listing_count=listing_count,
        )


# ============================================================
# ScrapeRun
# ============================================================

class ScrapeRunOut(BaseModel):
    """Public shape of one scrape_runs row."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_slug: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    listings_inserted: int
    listings_updated: int
    listings_errored: int
    error_message: Optional[str] = None

    @classmethod
    def from_scrape_run(cls, run: "ScrapeRun") -> "ScrapeRunOut":
        duration = None
        if run.finished_at and run.started_at:
            duration = (run.finished_at - run.started_at).total_seconds()
        return cls(
            id=run.id,
            source_slug=run.source.slug if run.source else "",
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_seconds=duration,
            listings_inserted=run.listings_inserted,
            listings_updated=run.listings_updated,
            listings_errored=run.listings_errored,
            error_message=run.error_message,
        )
        
# ============================================================
# Dashboard / Operations
# ============================================================

class ProviderListingCount(BaseModel):
    """A provider name + its current listing count."""
    provider_slug: str
    provider_name: str
    listing_count: int


class DashboardSummary(BaseModel):
    """Top-level dashboard health summary.

    Combines totals, last-24h activity counts, per-provider breakdown,
    and an overall health verdict with a human-readable reason.
    """
    total_listings: int = Field(description="Total non-duplicate listings.")
    duplicate_listings: int = Field(description="Count of listings marked as duplicates of another row.")
    canonical_listings: int = Field(description="Listings not marked as duplicates.")

    runs_last_24h_total: int
    runs_last_24h_success: int
    runs_last_24h_partial: int
    runs_last_24h_failed: int
    runs_last_24h_running: int

    by_provider: list[ProviderListingCount]

    health_status: str = Field(description="One of 'green', 'yellow', 'red'.")
    health_reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation when status is yellow/red. None when green.",
    )


class SourceStatus(BaseModel):
    """Per-source operational status row for the dashboard."""
    source_id: int
    source_slug: str
    provider_slug: str
    provider_name: str
    listing_count: int

    last_run_started_at: Optional[datetime] = None
    last_run_finished_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_duration_seconds: Optional[float] = None

    last_successful_run_at: Optional[datetime] = None
    last_error_message: Optional[str] = Field(
        default=None,
        description="Error message from the most recent failed run, if any. None if no recent failures.",
    )
    
# ============================================================
# Subscribers
# ============================================================

class SubscriberCreate(BaseModel):
    """Request body for POST /subscribers."""
    email: str = Field(min_length=3, max_length=320)


class SubscriberCreateResponse(BaseModel):
    """Response from POST /subscribers.

    Always returns 200 with already_subscribed flag — we don't expose
    whether an email is new vs. already in our list (privacy + spam prevention).
    """
    ok: bool = True
    already_subscribed: bool