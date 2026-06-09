"""Read endpoints for scrape_runs — operational visibility over HTTP.

Endpoints:
- GET /scrape_runs              → list recent runs (existing)
- GET /scrape_runs/dashboard    → top-level dashboard summary (new)
- GET /scrape_runs/by-source    → per-source operational status (new)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from vetce.api.deps import get_session
from vetce.api.schemas import (
    DashboardSummary,
    ProviderListingCount,
    ScrapeRunOut,
    SourceStatus,
)
from vetce.models import Listing, Provider, ScrapeRun, Source


router = APIRouter(prefix="/scrape_runs", tags=["scrape_runs"])


# ----------------------------------------------------------------------
# List endpoint (unchanged)
# ----------------------------------------------------------------------

@router.get(
    "",
    response_model=list[ScrapeRunOut],
    summary="List recent scrape runs (most recent first)",
)
def list_scrape_runs(
    limit: int = Query(default=20, ge=1, le=100),
    source: str | None = Query(default=None, description="Optional source slug filter"),
    status: str | None = Query(
        default=None,
        description="Optional status filter: success | partial | failed | running",
    ),
    session: Session = Depends(get_session),
) -> list[ScrapeRunOut]:
    stmt = (
        select(ScrapeRun)
        .options(selectinload(ScrapeRun.source))
        .order_by(ScrapeRun.started_at.desc())
    )
    if source:
        stmt = stmt.join(Source, ScrapeRun.source_id == Source.id).where(
            Source.slug == source
        )
    if status:
        stmt = stmt.where(ScrapeRun.status == status)
    stmt = stmt.limit(limit)
    runs = session.scalars(stmt).all()
    return [ScrapeRunOut.from_scrape_run(r) for r in runs]


# ----------------------------------------------------------------------
# Dashboard summary
# ----------------------------------------------------------------------

@router.get(
    "/dashboard",
    response_model=DashboardSummary,
    summary="Top-level dashboard summary: totals, 24h activity, health verdict",
)
def get_dashboard_summary(session: Session = Depends(get_session)) -> DashboardSummary:
    """Compute the dashboard summary.

    Single endpoint; queries are independent so we do them sequentially.
    Total query count is ~5 — small constant, fine to do inline.
    """
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)

    # --- Listings totals (canonical = not marked as duplicate) ---
    canonical_count = session.scalar(
        select(func.count(Listing.id)).where(Listing.duplicate_of.is_(None))
    ) or 0
    duplicate_count = session.scalar(
        select(func.count(Listing.id)).where(Listing.duplicate_of.is_not(None))
    ) or 0
    # "Total listings" in the dashboard sense = canonical (what users see).
    # Duplicates are reported separately so we can spot dedup activity.
    total_listings = canonical_count

    # --- Last-24h activity counts by status ---
    status_counts_rows = session.execute(
        select(ScrapeRun.status, func.count(ScrapeRun.id))
        .where(ScrapeRun.started_at >= cutoff_24h)
        .group_by(ScrapeRun.status)
    ).all()
    status_counts: dict[str, int] = {row[0]: row[1] for row in status_counts_rows}
    runs_24h_success = status_counts.get("success", 0)
    runs_24h_partial = status_counts.get("partial", 0)
    runs_24h_failed = status_counts.get("failed", 0)
    runs_24h_running = status_counts.get("running", 0)
    runs_24h_total = sum(status_counts.values())

    # --- Per-provider canonical listing counts ---
    by_provider_rows = session.execute(
        select(
            Provider.slug,
            Provider.name,
            func.count(Listing.id),
        )
        .join(Listing, Listing.provider_id == Provider.id)
        .where(Listing.duplicate_of.is_(None))
        .group_by(Provider.id, Provider.slug, Provider.name)
        .order_by(func.count(Listing.id).desc())
    ).all()
    by_provider = [
        ProviderListingCount(
            provider_slug=slug,
            provider_name=name,
            listing_count=count,
        )
        for slug, name, count in by_provider_rows
    ]

    # --- Health verdict ---
    health_status, health_reason = _compute_health(session, now)

    return DashboardSummary(
        total_listings=total_listings,
        duplicate_listings=duplicate_count,
        canonical_listings=canonical_count,
        runs_last_24h_total=runs_24h_total,
        runs_last_24h_success=runs_24h_success,
        runs_last_24h_partial=runs_24h_partial,
        runs_last_24h_failed=runs_24h_failed,
        runs_last_24h_running=runs_24h_running,
        by_provider=by_provider,
        health_status=health_status,
        health_reason=health_reason,
    )


# ----------------------------------------------------------------------
# Per-source status
# ----------------------------------------------------------------------

@router.get(
    "/by-source",
    response_model=list[SourceStatus],
    summary="Per-source operational status: last run, listing count, last error",
)
def get_status_by_source(session: Session = Depends(get_session)) -> list[SourceStatus]:
    """One row per active source. Heavy-ish — does up to 3 lookups per source.

    With <10 sources this is fine. Becomes a problem at ~100; if we ever hit
    that scale, refactor to a single window-function query.
    """
    sources = session.scalars(
        select(Source)
        .options(selectinload(Source.provider))
        .order_by(Source.slug)
    ).all()

    out: list[SourceStatus] = []
    for source in sources:
        # Listing count for this source (canonical only)
        listing_count = session.scalar(
            select(func.count(Listing.id)).where(
                and_(
                    Listing.source_id == source.id,
                    Listing.duplicate_of.is_(None),
                )
            )
        ) or 0

        # Most recent run (any status)
        last_run = session.scalar(
            select(ScrapeRun)
            .where(ScrapeRun.source_id == source.id)
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )

        # Most recent SUCCESSFUL run
        last_success = session.scalar(
            select(ScrapeRun)
            .where(
                and_(
                    ScrapeRun.source_id == source.id,
                    ScrapeRun.status == "success",
                )
            )
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )

        # Only surface an error message if the MOST RECENT run failed.
        # Once a source has succeeded after a failure, we consider the error
        # resolved — historical errors aren't surfaced on the dashboard.
        last_error_message: str | None = None
        if last_run is not None and last_run.status == "failed":
            last_error_message = last_run.error_message

        last_run_duration: float | None = None
        if last_run and last_run.finished_at and last_run.started_at:
            last_run_duration = (
                last_run.finished_at - last_run.started_at
            ).total_seconds()

        out.append(
            SourceStatus(
                source_id=source.id,
                source_slug=source.slug,
                provider_slug=source.provider.slug if source.provider else "",
                provider_name=source.provider.name if source.provider else "",
                listing_count=listing_count,
                last_run_started_at=last_run.started_at if last_run else None,
                last_run_finished_at=last_run.finished_at if last_run else None,
                last_run_status=last_run.status if last_run else None,
                last_run_duration_seconds=last_run_duration,
                last_successful_run_at=(
                    last_success.started_at if last_success else None
                ),
                last_error_message=last_error_message,
            )
        )

    return out


# ----------------------------------------------------------------------
# Health computation (private helper)
# ----------------------------------------------------------------------

def _compute_health(
    session: Session, now: datetime
) -> tuple[str, str | None]:
    """Decide overall system health based on scrape_runs data.

    Rules (from spec):
      - GREEN: all sources have a successful run in last 36h, no failed runs in last 24h
      - YELLOW: any source's last success was 36-72h ago, OR any partial-status runs in last 24h
      - RED: any source's last success was >72h ago, OR any failed runs in last 24h

    Sources with NO successful run ever are treated as red — assumes the source
    should have run by now. Exception: sources with zero runs at all are skipped
    (newly added but never scheduled).
    """
    cutoff_24h = now - timedelta(hours=24)
    cutoff_36h = now - timedelta(hours=36)
    cutoff_72h = now - timedelta(hours=72)

    # --- Red trigger 1: any failed run in last 24h ---
    failed_recent = session.scalar(
        select(ScrapeRun)
        .options(selectinload(ScrapeRun.source))
        .where(
            and_(
                ScrapeRun.status == "failed",
                ScrapeRun.started_at >= cutoff_24h,
            )
        )
        .order_by(ScrapeRun.started_at.desc())
        .limit(1)
    )
    if failed_recent is not None:
        slug = failed_recent.source.slug if failed_recent.source else "unknown"
        return "red", f"{slug} had a failed run in the last 24 hours"

    # --- Source-level checks. Gather all sources, then check last-success age. ---
    sources = session.scalars(select(Source)).all()
    for source in sources:
        # Has this source ever run at all?
        any_run = session.scalar(
            select(ScrapeRun.id)
            .where(ScrapeRun.source_id == source.id)
            .limit(1)
        )
        if any_run is None:
            # Source exists but never ran — likely brand new. Skip, not a health issue.
            continue

        last_success = session.scalar(
            select(ScrapeRun.started_at)
            .where(
                and_(
                    ScrapeRun.source_id == source.id,
                    ScrapeRun.status == "success",
                )
            )
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )

        if last_success is None:
            # Has runs but no successful one. That's red.
            return "red", f"{source.slug} has never had a successful run"

        if last_success < cutoff_72h:
            return "red", (
                f"{source.slug} hasn't had a successful run in over 72 hours"
            )

    # --- Yellow trigger 1: any partial runs in last 24h ---
    partial_recent = session.scalar(
        select(ScrapeRun)
        .options(selectinload(ScrapeRun.source))
        .where(
            and_(
                ScrapeRun.status == "partial",
                ScrapeRun.started_at >= cutoff_24h,
            )
        )
        .order_by(ScrapeRun.started_at.desc())
        .limit(1)
    )
    if partial_recent is not None:
        slug = partial_recent.source.slug if partial_recent.source else "unknown"
        return "yellow", f"{slug} had a partial-status run in the last 24 hours"

    # --- Yellow trigger 2: any source 36-72h since last success ---
    for source in sources:
        last_success = session.scalar(
            select(ScrapeRun.started_at)
            .where(
                and_(
                    ScrapeRun.source_id == source.id,
                    ScrapeRun.status == "success",
                )
            )
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )
        if last_success is not None and last_success < cutoff_36h:
            hours_ago = int((now - last_success).total_seconds() / 3600)
            return "yellow", (
                f"{source.slug}'s last successful run was {hours_ago} hours ago"
            )

    # All clear.
    return "green", None