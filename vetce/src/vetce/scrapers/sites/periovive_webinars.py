"""Scraper for Periovive upcoming webinars (periovive.com/webinars).

Source page: periovive.com/webinars

Structure:
- Wix-hosted site running the Wix Events app.
- The page SSR's a <script id="wix-warmup-data"> JSON blob containing fully
  structured event data: title, description, slug, start/end ISO timestamps,
  timezone, location, image URL, and the external Zoom registration URL.
- We parse the JSON directly rather than scraping the obfuscated CSS-class
  HTML, which Wix regenerates on every deploy.

This is a fourth extraction pattern: embedded JSON warmup data. No HTML
walking, no per-element class names, no regex on rendered text.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Iterable

import httpx
from selectolax.parser import HTMLParser

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


# Stable Wix Events app definition ID. Same across every Wix site that has
# the Events app installed; safe to hardcode.
WIX_EVENTS_APP_DEF_ID = "140603ad-af8d-84a5-2c80-a0f60cb47351"

EVENT_DETAILS_BASE = "https://www.periovive.com/event-details"


# ---------- JSON extraction ----------

def _extract_warmup_json(html: str) -> dict[str, Any]:
    """Pull the wix-warmup-data JSON blob out of the page."""
    tree = HTMLParser(html)
    node = tree.css_first("script#wix-warmup-data")
    if node is None:
        raise ValueError("wix-warmup-data script tag not found in page")
    try:
        return json.loads(node.text())
    except json.JSONDecodeError as e:
        raise ValueError(f"wix-warmup-data JSON parse failed: {e}") from e


def _extract_events(warmup: dict[str, Any]) -> list[dict[str, Any]]:
    """Find the Events widget data inside appsWarmupData.events.events."""
    apps = warmup.get("appsWarmupData", {})
    app_block = apps.get(WIX_EVENTS_APP_DEF_ID)
    if not app_block:
        raise ValueError(
            f"Wix Events app block ({WIX_EVENTS_APP_DEF_ID}) "
            "not found in warmup data"
        )
    # Widget key is per-instance (e.g. 'widgetcomp-mizjqege1') so we iterate
    # values and pick the first one that holds an events.events list.
    for widget_value in app_block.values():
        if not isinstance(widget_value, dict):
            continue
        events_section = widget_value.get("events")
        if isinstance(events_section, dict) and isinstance(
            events_section.get("events"), list
        ):
            return events_section["events"]
    raise ValueError("No Wix Events widget with events.events array found")


# ---------- Date / field parsing ----------

def _parse_iso_utc_to_date(value: str | None) -> date | None:
    """Parse '2026-06-19T01:00:00.000Z' -> date object (UTC date).

    NOTE: This returns the UTC date, which may be one day ahead of the
    local event date for late-evening US webinars. Caller should prefer
    startDateFormatted when possible.
    """
    if not value:
        return None
    s = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


# "June 18, 2026" / "Aug 20, 2026"
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_formatted_date(text: str | None) -> date | None:
    """Parse Wix's 'June 18, 2026' / 'Aug 20, 2026' format into a date."""
    if not text:
        return None
    parts = text.replace(",", "").strip().split()
    if len(parts) < 3:
        return None
    month_name, day_str, year_str = parts[0], parts[1], parts[2]
    month = _MONTHS.get(month_name.lower())
    if month is None:
        return None
    try:
        return date(int(year_str), month, int(day_str))
    except ValueError:
        return None


# ---------- Mapping to RawListing ----------

def _event_to_raw_listing(ev: dict[str, Any]) -> RawListing | None:
    title = (ev.get("title") or "").strip()
    if not title:
        return None

    slug = ev.get("slug")
    source_url = (
        f"{EVENT_DETAILS_BASE}/{slug}" if slug else PerioviveWebinarsScraper.LISTINGS_URL
    )

    scheduling = ev.get("scheduling") or {}
    # Prefer the pre-formatted local date string Wix already computed; fall
    # back to parsing the UTC ISO. The UTC value can be one day ahead of the
    # actual event date for evening US webinars.
    starts_at = _parse_formatted_date(scheduling.get("startDateFormatted"))
    if starts_at is None:
        config = scheduling.get("config") or {}
        starts_at = _parse_iso_utc_to_date(config.get("startDate"))

    ends_at = _parse_formatted_date(scheduling.get("endDateFormatted"))
    if ends_at is None:
        config = scheduling.get("config") or {}
        ends_at = _parse_iso_utc_to_date(config.get("endDate"))

    # Wix description is short here ("Free RACE Approved Webinar").
    # Pad it with the time string so the listing card has something useful.
    description_parts: list[str] = []
    raw_desc = (ev.get("description") or "").strip()
    if raw_desc:
        description_parts.append(raw_desc)
    formatted_time = scheduling.get("formatted")
    if formatted_time:
        description_parts.append(formatted_time)
    description = " | ".join(description_parts) if description_parts else None

    # Location.type == 1 in this Wix dataset means online; the location.name
    # is the human label ("Webinar").
    location = ev.get("location") or {}
    location_name = (location.get("name") or "").strip().lower()
    fmt = "live" if location_name == "webinar" or location.get("type") == 1 else None

    # Honest signals only. RACE approval is asserted directly by the provider
    # in the description string, so True is safe. Cost we leave None unless we
    # know the canonical field type.
    race_approved: bool | None = None
    if raw_desc and "race" in raw_desc.lower():
        race_approved = True

    # External Zoom registration link if Wix exposes one. Path is
    # registration.external.registration (the outer 'registration' is the
    # signup-config block; the inner one is the actual URL).
    # We deliberately do NOT fall back to source_url — that's stored
    # separately, and conflating the two hides whether we have a real link.
    reg_block = ev.get("registration") or {}
    external_block = reg_block.get("external") or {}
    external_reg = external_block.get("registration")
    registration_url = external_reg if external_reg else None

    return RawListing(
        source_slug=PerioviveWebinarsScraper.SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider=PerioviveWebinarsScraper.PROVIDER_NAME,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        format=fmt,
        cost=None,
        race_approved=race_approved,
        credit_hours=None,  # not present in listings JSON
        audience=None,      # not present in listings JSON
        registration_url=registration_url,
    )


# ---- The scraper class itself ----

class PerioviveWebinarsScraper(BaseScraper):
    SOURCE_SLUG = "periovive_webinars"
    PROVIDER_NAME = "Periovive"
    LISTINGS_URL = "https://www.periovive.com/webinars"

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        # client is unused — all data is in the warmup JSON on the listings page.
        warmup = _extract_warmup_json(listings_html)
        raw_events = _extract_events(warmup)
        log.info("periovive_webinars_found", count=len(raw_events))

        for i, ev in enumerate(raw_events, start=1):
            listing = _event_to_raw_listing(ev)
            if listing is None:
                log.info("periovive_skipped_empty_title", n=i, event_id=ev.get("id"))
                continue
            log.info(
                "periovive_webinar_parsed",
                n=i,
                title=listing.title,
                starts_at=str(listing.starts_at),
                race_approved=listing.race_approved,
                has_registration=bool(listing.registration_url),
            )
            yield listing


if __name__ == "__main__":
    PerioviveWebinarsScraper().run()