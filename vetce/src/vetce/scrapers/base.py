"""Base class for all scrapers.

Provides the truly-shared mechanics — HTTP client, polite fetching, 
entry-point wiring — without dictating how extraction works.

Subclasses MUST set SOURCE_SLUG and LISTINGS_URL, and MUST implement
extract_listings(). Everything else is optional.

Design principles:
- Subclasses produce RawListing objects. The base never builds them.
- Subclasses decide how to extract. The base provides fetch + lifecycle.
- The base is small (≈80 lines). If it grows past 200, something is wrong.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import ClassVar, Iterable

import httpx

from vetce.config import settings
from vetce.logging import configure_logging, log
from vetce.pipeline.ingest import run_ingest
from vetce.scrapers.types import RawListing


class BaseScraper(ABC):
    """Abstract base class for site scrapers.

    Subclass contract:
        SOURCE_SLUG    : str   — matches a row in the `sources` table
        LISTINGS_URL   : str   — the canonical entry-point URL
        PROVIDER_NAME  : str   — human-readable provider name (used in RawListing.provider)
        REQUEST_DELAY  : float — seconds between consecutive fetches (default 0)
        extract_listings(html, client) -> Iterable[RawListing]
                              — given the listings-page HTML and an HTTP
                                client (for any follow-up fetches), yield
                                RawListing objects.
    """

    # ---- Class attributes the subclass must define ----
    SOURCE_SLUG: ClassVar[str]
    LISTINGS_URL: ClassVar[str]
    PROVIDER_NAME: ClassVar[str]

    # ---- Class attributes with sensible defaults ----
    REQUEST_DELAY: ClassVar[float] = 0.0  # seconds between requests
    TIMEOUT_SECONDS: ClassVar[float] = 20.0

    # ---- HTTP helpers (rarely overridden) ----

    def make_client(self) -> httpx.Client:
        """Build the HTTP client used for all requests in this scraper.

        Override only if a site needs special headers, cookies, or auth.
        """
        return httpx.Client(
            headers={"User-Agent": settings.user_agent},
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def fetch(self, url: str, client: httpx.Client) -> str:
        """Fetch a URL, log it, and return the response body as text.

        Applies REQUEST_DELAY *before* the request. Raises on non-2xx.
        """
        if self.REQUEST_DELAY > 0:
            time.sleep(self.REQUEST_DELAY)
        log.info("fetch", url=url, scraper=self.SOURCE_SLUG)
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text

    # ---- Subclasses implement this ----

    @abstractmethod
    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        """Yield RawListing objects given the listings-page HTML.

        Receives an httpx.Client so the subclass can do follow-up fetches
        for detail pages if needed.
        """

    def list_pages(self) -> Iterable[str]:
        """Yield each listings-page URL to fetch.

        Default: single page at LISTINGS_URL. Override for paginated sites.
        Subclasses that paginate should yield URLs one at a time; the loop
        stops the moment a page yields no listings.
        """
        yield self.LISTINGS_URL

    def scrape(self) -> Iterable[RawListing]:
        """Fetch each listings page and delegate to extract_listings.

        Stops paginating as soon as a page yields zero listings — this lets
        subclasses set a generous MAX_PAGES without paying for empty fetches
        beyond the real end.
        """
        with self.make_client() as client:
            for url in self.list_pages():
                html = self.fetch(url, client)
                page_count = 0
                for listing in self.extract_listings(html, client):
                    page_count += 1
                    yield listing
                if page_count == 0:
                    # Empty page → assume we've gone past the end. Stop early.
                    log.info(
                        "scrape_paginate_stop",
                        scraper=self.SOURCE_SLUG,
                        url=url,
                    )
                    break

    def run(self, tag_after: bool = True) -> dict[str, int]:
        """Configure logging, run the ingest pipeline, return the counts.

        Designed to be called from a scraper module's `__main__` block.

        tag_after: if True (the default), runs the tagger as a subprocess
        immediately after ingesting. Scraping wipes subject_category on every
        row it touches, and the public API hides NULL-category listings --
        so a scrape not followed by tagging leaves listings persisted but
        silently invisible. Pass tag_after=False when the caller (e.g.
        run_all.py) already tags everything in one batch after running
        multiple scrapers, to avoid tagging redundantly per source.
        """
        configure_logging()
        counts = run_ingest(self.scrape, source_slug=self.SOURCE_SLUG)
        print(f"\nDone: {counts}")

        if tag_after:
            self._tag_untagged()

        return counts

    def _tag_untagged(self) -> None:
        """Run the tagger as a subprocess, exactly as invoked manually
        (`python -m vetce.pipeline.tag_all`). Only touches listings where
        subject_category IS NULL -- the tagger's own default behavior --
        so this never re-tags or disturbs already-tagged listings from
        other sources.
        """
        import subprocess
        import sys

        log.info("scraper_run_tagger_start", scraper=self.SOURCE_SLUG)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "vetce.pipeline.tag_all"],
                check=False,
            )
            if result.returncode != 0:
                log.error(
                    "scraper_run_tagger_nonzero_exit",
                    scraper=self.SOURCE_SLUG,
                    code=result.returncode,
                )
            else:
                log.info("scraper_run_tagger_done", scraper=self.SOURCE_SLUG)
        except Exception as e:
            log.error(
                "scraper_run_tagger_failed",
                scraper=self.SOURCE_SLUG,
                error=f"{type(e).__name__}: {e}",
            )