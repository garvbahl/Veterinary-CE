"""Scraper for Periovive webinars via the maintained JSON feed.

The old Periovive site (Wix) was replaced by a custom Vite/React SPA that
hardcodes webinar data in its JS bundle. Rather than parse a minified bundle,
the Periovive team exposes a clean JSON feed we consume directly:

    https://www.periovive.com/data/webinars.json

Feed shape (per webinar):
    title, speaker, date ("Jul 09, 2026"), time ("8:00 PM - 9:00 PM EST"),
    race_credits ("1 RACE-approved CE credit"), registration_url (may be null),
    status ("registration_closed" | ...), image (speaker headshot URL)

Mapping to RawListing:
    title            -> title
    speaker          -> presenter
    image            -> presenter_image_url
    date             -> starts_at (parsed)
    time             -> appended to description
    race_credits     -> credit_hours (extracted int) + race_approved (True)
    registration_url -> registration_url (null signals "registration closed";
                        the frontend renders a closed state when a live
                        Periovive listing has no registration URL)

These webinars have no unique per-event detail URL, so we synthesize a stable
source_url from a slugified title, keeping re-scrapes idempotent.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Iterable

import httpx

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


FEED_URL = "https://www.periovive.com/data/webinars.json"
SOURCE_BASE = "https://www.periovive.com/ce"


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:120] or "webinar"


def _parse_date(value: str | None) -> date | None:
    """Parse 'Jul 09, 2026' / 'Aug 20, 2026' into a date."""
    if not value:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_credits(value: str | None) -> float | None:
    """Extract the leading number from '1 RACE-approved CE credit'."""
    if not value:
        return None
    m = re.search(r"\d+(?:\.\d+)?", value)
    if not m:
        return None
    try:
        v = float(m.group(0))
        return v if v > 0 else None
    except ValueError:
        return None


def _webinar_to_raw_listing(w: dict[str, Any]) -> RawListing | None:
    title = (w.get("title") or "").strip()
    if not title:
        return None

    speaker = (w.get("speaker") or "").strip() or None
    image = (w.get("image") or "").strip() or None
    starts_at = _parse_date(w.get("date"))

    # Build description from time + status.
    desc_parts: list[str] = []
    time_str = (w.get("time") or "").strip()
    if time_str:
        desc_parts.append(time_str)
    if (w.get("status") or "").strip().lower() == "registration_closed":
        desc_parts.append("Registration is closed.")
    description = " | ".join(desc_parts) if desc_parts else None

    race_credits = w.get("race_credits")
    credit_hours = _parse_credits(race_credits)
    race_approved = bool(race_credits and "race" in race_credits.lower())

    registration_url = w.get("registration_url") or None

    # Synthesize a stable unique URL (feed has no per-event detail page).
    date_slug = starts_at.isoformat() if starts_at else "tbd"
    source_url = f"{SOURCE_BASE}#{_slugify(title)}-{date_slug}"

    return RawListing(
        source_slug=PerioviveWebinarsScraper.SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider=PerioviveWebinarsScraper.PROVIDER_NAME,
        description=description,
        starts_at=starts_at,
        ends_at=None,
        format="live",
        cost="Free",
        race_approved=race_approved,
        credit_hours=credit_hours,
        presenter=speaker,
        presenter_image_url=image,
        audience=None,
        registration_url=registration_url,
    )


class PerioviveWebinarsScraper(BaseScraper):
    SOURCE_SLUG = "periovive_webinars"
    PROVIDER_NAME = "Periovive"
    LISTINGS_URL = FEED_URL

    def make_client(self) -> httpx.Client:
        return httpx.Client(
            headers={"User-Agent": "VetCEBot/0.1", "Accept": "application/json"},
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        try:
            data = json.loads(listings_html)
        except json.JSONDecodeError as e:
            raise ValueError(f"periovive webinars feed JSON parse failed: {e}") from e

        webinars = data.get("webinars")
        if not isinstance(webinars, list):
            raise ValueError("periovive webinars feed missing 'webinars' array")

        synced = data.get("synced_at")
        log.info("periovive_feed_loaded", count=len(webinars), synced_at=synced)

        for i, w in enumerate(webinars, start=1):
            listing = _webinar_to_raw_listing(w)
            if listing is None:
                log.info("periovive_skipped_empty_title", n=i)
                continue
            log.info(
                "periovive_webinar_parsed",
                n=i,
                title=listing.title,
                presenter=listing.presenter,
                starts_at=str(listing.starts_at),
                has_image=bool(listing.presenter_image_url),
                closed=listing.registration_url is None,
            )
            yield listing


if __name__ == "__main__":
    PerioviveWebinarsScraper().run()