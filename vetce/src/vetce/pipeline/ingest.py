"""Pipeline step: orchestrate a scraper run end-to-end.

Calls a scraper's scrape() function, persists each RawListing into the database
via the persist module, and logs a summary.
"""
from __future__ import annotations

from typing import Callable, Iterable

from vetce.db import SessionLocal
from vetce.logging import log
from vetce.pipeline.persist import persist_listings
from vetce.scrapers.types import RawListing


def run_ingest(scrape_fn: Callable[[], Iterable[RawListing]],
               source_slug: str) -> dict[str, int]:
    """Run a single scraper and persist its output.

    Parameters:
        scrape_fn: a callable that yields RawListing objects (typically scrape from
                   a sites/<provider>.py module).
        source_slug: the slug of the Source row this scraper produces listings for
                     (must match what was seeded into the sources table).

    Returns a dict of counts: {"inserted": N, "updated": N, "errors": N}.
    """
    log.info("ingest_start", source=source_slug)
    listings = list(scrape_fn())  # materialize the generator
    log.info("ingest_scraped", count=len(listings))

    with SessionLocal() as session:
        counts = persist_listings(session, listings, source_slug=source_slug)

    log.info("ingest_complete", source=source_slug, **counts)
    return counts