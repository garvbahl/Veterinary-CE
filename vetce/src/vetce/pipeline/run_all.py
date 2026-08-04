"""Run every scraper once and tag new listings.

This is the one-shot entry point for the nightly automated run (invoked by the
GitHub Actions workflow). Unlike scheduler.py (a persistent APScheduler process),
this runs everything a single time and exits -- suitable for a cron-triggered
CI job.

Run with:
    uv run python -m vetce.pipeline.run_all
    uv run python -m vetce.pipeline.run_all --no-tag      # skip the tagger

Flow:
  1. For each scraper in SCRAPER_REGISTRY: call .run(). Each run records its own
     scrape_runs row (success/failed/partial) and returns counts. We catch any
     exception so one scraper's failure never stops the rest.
  2. Run the tagger (tag_all) so newly scraped listings get categories.
  3. Log a per-source summary, flagging failures and zero-result (silent) runs.

Monitoring: the script exits non-zero if any scraper failed, so the GitHub
Actions run is marked red. GitHub's built-in workflow-failure notifications
then alert us -- no custom email system needed. Per-run detail is also visible
in the scrape_runs table and in the Actions run log.
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from vetce.db import SessionLocal
from vetce.logging import configure_logging, log
from vetce.models import Source
from vetce.scrapers.registry import SCRAPER_REGISTRY


@dataclass
class SourceResult:
    """One row in the run summary."""
    slug: str
    ok: bool
    inserted: int
    updated: int
    errors: int
    error_message: str | None

    @property
    def total_listings(self) -> int:
        return self.inserted + self.updated

    @property
    def is_zero(self) -> bool:
        """Ran without raising, but produced no listings -- the silent failure."""
        return self.ok and self.total_listings == 0


def _run_all_scrapers() -> list[SourceResult]:
    """Run every registered scraper once. Never raises -- captures per-scraper
    failures into the result list so one bad scraper doesn't halt the batch.
    """
    results: list[SourceResult] = []
    for slug, scraper_cls in SCRAPER_REGISTRY.items():
        name = scraper_cls.__name__
        log.info("run_all_scraper_start", scraper=name, slug=slug)
        try:
            counts = scraper_cls().run()
            results.append(SourceResult(
                slug=slug,
                ok=counts.get("errors", 0) == 0,
                inserted=counts.get("inserted", 0),
                updated=counts.get("updated", 0),
                errors=counts.get("errors", 0),
                error_message=None,
            ))
            log.info("run_all_scraper_done", scraper=name, **counts)
        except Exception as e:
            # The scraper raised before/outside run_ingest's own handling.
            msg = f"{type(e).__name__}: {e}"
            results.append(SourceResult(
                slug=slug, ok=False, inserted=0, updated=0, errors=1,
                error_message=msg,
            ))
            log.error("run_all_scraper_failed", scraper=name, error=msg)
    return results


def _run_tagger() -> bool:
    """Tag newly scraped (untagged) listings. Scraping wipes subject_category,
    so this must run after the scrapers.

    Runs tag_all as a subprocess -- exactly how it's invoked manually
    (`python -m vetce.pipeline.tag_all`). This avoids argparse collisions with
    run_all's own arguments and keeps the tagger isolated in its own process.

    Returns True on success, False on failure. A tagger failure is serious: a
    scrape wipes subject_category, and the listings API hides NULL-category
    listings, so if the tagger doesn't run the whole site silently drops to a
    handful of listings. The caller treats False as a hard failure.
    """
    import subprocess
    import sys

    log.info("run_all_tagger_start")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "vetce.pipeline.tag_all"],
            check=False,
        )
        if result.returncode != 0:
            log.error("run_all_tagger_nonzero_exit", code=result.returncode)
            return False
        log.info("run_all_tagger_done")
        return True
    except Exception as e:
        log.error("run_all_tagger_failed", error=f"{type(e).__name__}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all scrapers and tag new listings.")
    parser.add_argument("--no-tag", action="store_true", help="Skip the tagger step.")
    args = parser.parse_args()

    configure_logging()
    started = datetime.now(timezone.utc)
    t0 = time.time()
    log.info("run_all_start", scrapers=len(SCRAPER_REGISTRY))

    results = _run_all_scrapers()

    tagger_ok = True
    if not args.no_tag:
        tagger_ok = _run_tagger()

    elapsed = time.time() - t0
    failures = [r for r in results if not r.ok]
    zeros = [r for r in results if r.is_zero]

    log.info(
        "run_all_complete",
        total=len(results),
        failures=len(failures),
        zeros=len(zeros),
        tagger_ok=tagger_ok,
        elapsed_sec=round(elapsed, 1),
    )

    # Log per-source detail so it's visible in the GitHub Actions run log.
    for r in results:
        if not r.ok:
            log.error("run_all_source_failed", source=r.slug, error=r.error_message)
        elif r.is_zero:
            log.warning("run_all_source_empty", source=r.slug)
        else:
            log.info(
                "run_all_source_ok",
                source=r.slug,
                listings=r.total_listings,
                inserted=r.inserted,
                updated=r.updated,
            )

    if not tagger_ok:
        log.error(
            "run_all_tagger_failure_is_critical",
            hint="scraping wipes subject_category; without tagging, the site "
                 "hides NULL-category listings and drops to a handful shown.",
        )

    # Non-zero exit if any scraper failed OR the tagger failed. A tagger failure
    # is critical: it leaves listings NULL-categorized, which the API hides, so
    # the site silently empties. Failing loudly triggers GitHub's built-in
    # workflow-failure notification -- no custom email needed.
    if failures or not tagger_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()