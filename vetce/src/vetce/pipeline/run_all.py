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

Monitoring: the run exits non-zero (red GitHub run + built-in failure email) if
the tagger fails, or if a majority of scrapers fail (a systemic problem). A few
individual scraper failures -- expected in cloud scraping when a source blocks
or changes -- are logged but tolerated, keeping the run green. Per-run detail is
in the scrape_runs table and the Actions run log.
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


# If more than this fraction of scrapers fail in one run, treat it as a
# systemic problem (e.g. all datacenter IPs blocked, network down) and fail
# the whole run. A few individual failures -- a site changed, one source
# rate-limited or IP-blocked us -- are expected in cloud scraping and only get
# logged, not escalated to a red run. The tagger failing ALWAYS fails the run
# regardless, since that silently empties the site.
SCRAPER_FAILURE_FRACTION_THRESHOLD = 0.5


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
            # tag_after=False: run_all tags everything once in a single
            # batch after this loop finishes, so each individual scraper
            # shouldn't also trigger its own tagger subprocess.
            counts = scraper_cls().run(tag_after=False)
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

    # Decide whether this run counts as a failure.
    #
    # - Tagger failure -> ALWAYS fail. It leaves listings NULL-categorized, which
    #   the API hides, so the site silently empties. This must be loud.
    # - Scraper failures -> tolerate a few. Individual sources getting blocked,
    #   rate-limited, or changing their HTML is normal in cloud scraping; the
    #   other sources and the tagger still did their job. Only escalate to a
    #   failed run if MOST scrapers failed, which signals a systemic issue
    #   (network, all IPs blocked) rather than one flaky source.
    total = len(results)
    too_many_scrapers_failed = (
        total > 0 and len(failures) / total > SCRAPER_FAILURE_FRACTION_THRESHOLD
    )
    if too_many_scrapers_failed:
        log.error(
            "run_all_too_many_scrapers_failed",
            failed=len(failures),
            total=total,
            hint="a majority of scrapers failed -- likely systemic (network, "
                 "IP blocks) rather than one flaky source.",
        )
    elif failures:
        # Some failed, but within tolerance. Note it clearly, stay green.
        log.warning(
            "run_all_some_scrapers_failed_tolerated",
            failed=len(failures),
            total=total,
            failed_sources=[r.slug for r in failures],
        )

    if not tagger_ok or too_many_scrapers_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()