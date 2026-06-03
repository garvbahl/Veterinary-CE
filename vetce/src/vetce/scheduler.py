"""Scheduled execution of all scrapers, driven by per-source cron expressions
stored in the `sources` table.

Run with:
    uv run python -m vetce.scheduler

Reads SCHEDULER_MODE from .env:
  - "prod" — each scraper runs on the cron schedule stored in its source row.
             If a source has no cron_expression, that scraper is not scheduled.
  - "dev"  — each scraper runs every 5 minutes, staggered, ignoring the database.
             Useful for testing the scheduler without waiting for production cron times.

To change a scraper's schedule in prod: update its source's cron_expression
in the database, then restart this process. No code deploy needed.

The process runs forever. Ctrl+C to stop gracefully.
"""
from __future__ import annotations

import signal
import sys
import time
from typing import Type

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from vetce.config import settings
from vetce.db import SessionLocal
from vetce.logging import configure_logging, log
from vetce.models import Source
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.sites.cornell_cvm import CornellCvmScraper
from vetce.scrapers.sites.navta import NavtaScraper
from vetce.scrapers.sites.vetmedteam import VetMedTeamScraper


# Maps source.slug -> the scraper class that handles it.
# When we add new scrapers, add them here.
SCRAPER_REGISTRY: dict[str, Type[BaseScraper]] = {
    VetMedTeamScraper.SOURCE_SLUG: VetMedTeamScraper,
    NavtaScraper.SOURCE_SLUG: NavtaScraper,
    CornellCvmScraper.SOURCE_SLUG: CornellCvmScraper,
}


def _run_scraper(scraper_cls: Type[BaseScraper]) -> None:
    """Run one scraper. Called by APScheduler when each trigger fires."""
    name = scraper_cls.__name__
    log.info("scheduler_job_start", scraper=name)
    try:
        counts = scraper_cls().run()
        log.info("scheduler_job_done", scraper=name, **counts)
    except Exception as e:
        # Don't let one scraper's failure kill the scheduler.
        # run_ingest already recorded the failure to scrape_runs;
        # we just need to keep the scheduler alive.
        log.error(
            "scheduler_job_failed",
            scraper=name,
            error=f"{type(e).__name__}: {e}",
        )


def _load_sources_from_db() -> list[Source]:
    """Read all sources from the database (one snapshot at startup)."""
    with SessionLocal() as s:
        return list(s.scalars(select(Source).order_by(Source.id)).all())


def _register_jobs(scheduler: BackgroundScheduler, mode: str) -> int:
    """Register one job per source. Returns the number of jobs registered."""
    sources = _load_sources_from_db()
    registered = 0

    for i, source in enumerate(sources):
        scraper_cls = SCRAPER_REGISTRY.get(source.slug)
        if scraper_cls is None:
            log.warning(
                "scheduler_no_scraper_for_source",
                slug=source.slug,
                hint="add the scraper to SCRAPER_REGISTRY in scheduler.py",
            )
            continue

        if mode == "dev":
            # Every 5 minutes, staggered by 30 seconds per scraper to avoid
            # all firing simultaneously when the interval boundary hits.
            # We compute the stagger as a proper datetime offset to avoid
            # bogus "00:00:60" strings.
            from datetime import datetime, timedelta, timezone
            stagger = timedelta(seconds=i * 30)
            base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            trigger = IntervalTrigger(
                minutes=5,
                start_date=base + stagger,
            )
            schedule_desc = f"every 5 min (dev), +{int(stagger.total_seconds())}s offset"

        elif mode == "prod":
            if not source.cron_expression:
                log.info(
                    "scheduler_source_not_scheduled",
                    slug=source.slug,
                    reason="cron_expression is empty",
                )
                continue
            try:
                trigger = CronTrigger.from_crontab(
                    source.cron_expression, timezone="UTC"
                )
            except ValueError as e:
                log.error(
                    "scheduler_bad_cron_expression",
                    slug=source.slug,
                    cron=source.cron_expression,
                    error=str(e),
                )
                continue
            schedule_desc = f"cron='{source.cron_expression}' UTC"

        else:
            raise ValueError(
                f"Unknown SCHEDULER_MODE: {mode!r}. Use 'dev' or 'prod'."
            )

        scheduler.add_job(
            _run_scraper,
            trigger=trigger,
            args=[scraper_cls],
            id=scraper_cls.__name__,
            name=scraper_cls.__name__,
            max_instances=1,         # never run two copies of same scraper at once
            coalesce=True,           # if multiple fires backed up, collapse to one
            misfire_grace_time=300,  # if we missed by <5 min, still run
        )
        log.info(
            "scheduler_job_registered",
            scraper=scraper_cls.__name__,
            source_slug=source.slug,
            schedule=schedule_desc,
        )
        registered += 1

    return registered


def main() -> None:
    configure_logging()

    mode = settings.scheduler_mode.lower()
    if mode not in ("dev", "prod"):
        raise ValueError(
            f"Invalid SCHEDULER_MODE={mode!r}. Set to 'dev' or 'prod' in .env."
        )

    log.info("scheduler_mode", mode=mode)

    scheduler = BackgroundScheduler(timezone="UTC")
    registered = _register_jobs(scheduler, mode)

    if registered == 0:
        log.error("scheduler_no_jobs_registered",
                  hint="check that sources have cron_expressions and "
                       "scrapers are in SCRAPER_REGISTRY")
        sys.exit(1)

    scheduler.start()
    log.info("scheduler_started", jobs_registered=registered)

    # Print upcoming runs so a human can see what's about to happen.
    for job in scheduler.get_jobs():
        log.info(
            "scheduler_next_run",
            scraper=job.id,
            next_run=str(job.next_run_time),
        )

    # Graceful shutdown on Ctrl+C / kill.
    def _shutdown(signum, frame):
        log.info("scheduler_shutdown_requested", signal=signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    # Sleep forever — the scheduler runs in background threads.
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()