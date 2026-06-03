"""Ingest pipeline: orchestrate one scraper run and persist its output.

Every call to run_ingest() produces:
  1. A `scrape_runs` row inserted in 'running' state before the scrape starts.
  2. That same row updated to 'success'/'partial'/'failed' when the scrape ends.

If the process crashes hard (no exception we can catch — e.g., OS kill,
machine reboot), the row stays in 'running' state. A separate health check
can detect these zombies.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable

from sqlalchemy import select

from vetce.db import SessionLocal
from vetce.logging import log
from vetce.models import ScrapeRun, Source
from vetce.pipeline.persist import persist_listings
from vetce.scrapers.types import RawListing


def _now() -> datetime:
    """Single source of truth for current time. Easier to mock in tests later."""
    return datetime.now(timezone.utc)


def _create_run_record(source_slug: str) -> int:
    """Create a scrape_runs row in 'running' state and return its id.

    Uses its own transaction so the row is durable before the scrape begins.
    """
    with SessionLocal() as s:
        source = s.scalar(select(Source).where(Source.slug == source_slug))
        if source is None:
            raise ValueError(f"Unknown source slug: {source_slug!r}")

        run = ScrapeRun(
            source_id=source.id,
            started_at=_now(),
            status="running",
            listings_inserted=0,
            listings_updated=0,
            listings_errored=0,
        )
        s.add(run)
        s.commit()
        return run.id


def _finalize_run_record(
    run_id: int,
    status: str,
    counts: dict[str, int],
    error_message: str | None = None,
) -> None:
    """Update a scrape_runs row with the final outcome.

    Uses its own transaction so this completes even if the main scrape
    transaction had to roll back.
    """
    with SessionLocal() as s:
        run = s.get(ScrapeRun, run_id)
        if run is None:
            log.error("scrape_run_finalize_missing", run_id=run_id)
            return
        run.finished_at = _now()
        run.status = status
        run.listings_inserted = counts.get("inserted", 0)
        run.listings_updated = counts.get("updated", 0)
        run.listings_errored = counts.get("errors", 0)
        run.error_message = error_message
        s.commit()


def run_ingest(
    scrape_fn: Callable[[], Iterable[RawListing]],
    source_slug: str,
) -> dict[str, int]:
    """Run one scraper, persist its output, record the run.

    Returns a dict with keys: inserted, updated, errors.
    """
    log.info("ingest_start", source=source_slug)

    # 1. Insert the 'running' row in its own transaction.
    run_id = _create_run_record(source_slug)
    log.info("scrape_run_started", run_id=run_id, source=source_slug)

    counts: dict[str, int] = {"inserted": 0, "updated": 0, "errors": 0}
    status = "running"
    error_message: str | None = None

    try:
        # 2. Run the scraper and persist what it yields.
        listings = list(scrape_fn())
        log.info("ingest_scraped", count=len(listings))

        with SessionLocal() as session:
            counts = persist_listings(
                session, listings, source_slug=source_slug
            )
            session.commit()

        # 3. Run quality checks scoped to this source. Failures here
        # are LOGGED but do not block — the data is already persisted,
        # we just want a human to know if something looks off.
        try:
            from vetce.quality import run_checks
            issues = run_checks(source_slug=source_slug)
            if issues:
                log.warning(
                    "ingest_quality_issues",
                    source=source_slug,
                    issue_count=len(issues),
                )
        except Exception as qc_err:
            # Don't let a broken quality check kill the ingest run.
            log.error(
                "ingest_quality_checks_failed",
                source=source_slug,
                error=f"{type(qc_err).__name__}: {qc_err}",
            )

        # 4. Decide success vs partial based on error count.
        if counts.get("errors", 0) > 0:
            status = "partial"
        else:
            status = "success"

    except Exception as e:
        status = "failed"
        error_message = f"{type(e).__name__}: {e}"
        log.error("ingest_failed", source=source_slug, error=error_message)
        # Re-raise after we've recorded the failure, so the caller still sees the crash.
        raise

    finally:
        # 4. Always update the run record, even on crash.
        _finalize_run_record(
            run_id=run_id,
            status=status,
            counts=counts,
            error_message=error_message,
        )
        log.info(
            "ingest_complete",
            source=source_slug,
            run_id=run_id,
            status=status,
            **counts,
        )

    return counts