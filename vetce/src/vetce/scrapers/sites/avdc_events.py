"""Scraper for AVDC events (avdc.org/events).

Source page: avdc.org/events/

Structure:
- WordPress site running the WP Event Manager plugin.
- Each event card on the listings page is an <a class="wpem-event-action-url">
  wrapping the title, date, location, and event type with stable wpem-* CSS
  classes.
- Detail pages have:
    <h3 class="wpem-heading-text">Date And Time</h3>
    <div class="wpem-event-date-time">...</div>
    <div class="wpem-event-location">...</div>
    <div class="wpem-event-category">...</div>
    <div class="wpem-event-type">...</div>
    <div class="registration_details"> with the external register URL
    <p class="wpem-additional-info-block-title">
      <strong>Region - </strong> ...
    </p>
    (similar labeled <p> for Audience, Instructors, etc.)
- The page <meta name="description"> contains a short summary like
  "(8 hours lecture, 8 hours lab)" — useful for credit_hours parsing.

This reuses the listings + detail-fetch pattern from periovive_thinkific.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing

import html as html_module


AVDC_BASE = "https://avdc.org"


# ---------- Date parsing ----------

# "08-06-2026 @ 08:00 AM" -> we just want the date portion.
_RE_DATE = re.compile(r"(\d{2})-(\d{2})-(\d{4})")


# Matches both "08-06-2026" (AVDC DOM format) and "2026-08-06" (JSON-LD format).
_RE_DATE_US = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
_RE_DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _parse_date(text: str) -> tuple[int, int, int] | None:
    """Pull a date out of a string in either MM-DD-YYYY or YYYY-MM-DD form.
    Returns (year, month, day)."""
    if not text:
        return None
    m = _RE_DATE_ISO.search(text)
    if m:
        year, month, day = m.groups()
    else:
        m = _RE_DATE_US.search(text)
        if not m:
            return None
        month, day, year = m.groups()
    try:
        return (int(year), int(month), int(day))
    except ValueError:
        return None


def _parse_date_range(text: str) -> tuple[
    tuple[int, int, int] | None, tuple[int, int, int] | None
]:
    """Pull two dates out of a string. Returns (start, end)."""
    if not text:
        return (None, None)
    matches = _RE_DATE.findall(text)
    if not matches:
        return (None, None)
    starts = (int(matches[0][2]), int(matches[0][0]), int(matches[0][1]))
    if len(matches) >= 2:
        ends = (int(matches[1][2]), int(matches[1][0]), int(matches[1][1]))
    else:
        ends = starts
    return (starts, ends)


# ---------- Credit hours parsing ----------

# Matches "8 hours lecture", "8 hours lab", "16 CE hours", "2.5 hours of CE"
_RE_HOURS = re.compile(
    r"(\d+(?:\.\d+)?)\s*hour",
    re.IGNORECASE,
)


def _parse_credit_hours(description: str) -> Decimal | None:
    """Sum every '<N> hour(s)' fragment in the description.

    AVDC writes things like '(8 hours lecture, 8 hours lab)' — we sum both
    because both count toward CE. If the description is bare, returns None.
    """
    if not description:
        return None
    matches = _RE_HOURS.findall(description)
    if not matches:
        return None
    try:
        total = sum(Decimal(m) for m in matches)
        return total if total > 0 else None
    except (ValueError, ArithmeticError):
        return None


# ---------- Listings page extraction ----------

def _extract_event_links(html: str) -> list[str]:
    """Return the detail-page URL for every event card on the listings page."""
    tree = HTMLParser(html)
    urls: list[str] = []
    seen: set[str] = set()
    for a in tree.css("a.wpem-event-action-url"):
        href = a.attributes.get("href")
        if not href or "/event/" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        urls.append(href)
    return urls


# ---------- Detail page extraction ----------

def _text_or_none(node: Node | None) -> str | None:
    if node is None:
        return None
    text = node.text(separator=" ", strip=True)
    return text or None


def _additional_info(tree: HTMLParser, label: str) -> str | None:
    """Find a <p class="wpem-additional-info-block-title"> whose <strong>
    text starts with the given label, and return the trailing text.

    Example: label="Instructors" returns
    "Kevin Stepaniuk, DVM, DAVDC, DEVDC and Alice Sievers, DVM, DAVDC".
    """
    label_lower = label.lower()
    for p in tree.css("p.wpem-additional-info-block-title"):
        strong = p.css_first("strong")
        if strong is None:
            continue
        strong_text = strong.text(strip=True).rstrip(":").rstrip("-").strip().lower()
        if not strong_text.startswith(label_lower):
            continue
        # The full <p> text includes both the strong label and the trailing value.
        full = p.text(separator=" ", strip=True)
        # Strip the leading "Label -" / "Label:" piece.
        stripped = re.sub(
            rf"^{re.escape(strong.text(strip=True))}\s*", "", full, count=1
        ).strip()
        # Remove a leading "- " if present.
        stripped = re.sub(r"^[-:]\s*", "", stripped)
        return stripped or None
    return None


def _extract_detail_fields(detail_html: str) -> dict:
    """Parse a detail page into a flat dict of fields.

    Prefers the JSON-LD <script type="application/ld+json"> Event block,
    which AVDC's WP Event Manager plugin emits with structured fields
    (name, startDate, endDate, location, description). Falls back to DOM
    parsing for anything JSON-LD doesn't cover (category, event type,
    register URL, additional-info fields).
    """
    import json

    tree = HTMLParser(detail_html)

    # --- JSON-LD first ---
    jsonld_name: str | None = None
    jsonld_description: str | None = None
    jsonld_start: str | None = None
    jsonld_end: str | None = None
    jsonld_location: str | None = None

    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text() or ""
        if "Event" not in raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("@type") != "Event":
            continue
        jsonld_name = html_module.unescape((data.get("name") or "").strip()) or None
        desc_html = data.get("description") or ""
        # AVDC wraps description in <p>...</p>. Strip tags lightly, decode entities.
        desc_stripped = re.sub(r"<[^>]+>", "", desc_html).strip()
        jsonld_description = html_module.unescape(desc_stripped) or None
        jsonld_start = data.get("startDate") or None
        jsonld_end = data.get("endDate") or None
        loc = data.get("Location") or data.get("location") or {}
        if isinstance(loc, dict):
            jsonld_location = (loc.get("name") or loc.get("address") or "").strip() or None
        elif isinstance(loc, str):
            jsonld_location = loc.strip() or None
        break

    # --- Title fallback ---
    title = jsonld_name
    if not title:
        title_node = tree.css_first("h1.entry-title") or tree.css_first("h1")
        title = _text_or_none(title_node)

    # --- Dates ---
    starts_tuple = _parse_date(jsonld_start) if jsonld_start else None
    ends_tuple = _parse_date(jsonld_end) if jsonld_end else None
    if starts_tuple is None or ends_tuple is None:
        # Fall back to the DOM date block.
        date_block = tree.css_first("div.wpem-event-date-time")
        date_text = _text_or_none(date_block) or ""
        s, e = _parse_date_range(date_text)
        starts_tuple = starts_tuple or s
        ends_tuple = ends_tuple or e

    # --- Location ---
    location = jsonld_location
    if not location:
        # DOM fallback: <h3>Location</h3> followed by a <div> with an <a>.
        for h3 in tree.css("h3.wpem-heading-text"):
            if h3.text(strip=True).lower() == "location":
                sibling = h3.next
                while sibling is not None and getattr(sibling, "tag", None) != "div":
                    sibling = sibling.next
                if sibling is not None:
                    location = _text_or_none(sibling)
                break
    if location:
        location = re.sub(r"\s+", " ", location).strip() or None

    # --- Event Category (AVDC taxonomy) ---
    category_block = tree.css_first("div.wpem-event-category")
    category_text = _text_or_none(category_block)

    # --- Event Type ---
    type_block = tree.css_first("div.wpem-event-type")
    type_text = _text_or_none(type_block)

    # --- Registration URL ---
    reg_block = tree.css_first("div.registration_details")
    register_url: str | None = None
    if reg_block is not None:
        a = reg_block.css_first("a[href]")
        if a is not None:
            register_url = a.attributes.get("href")

    # --- Description ---
    description = jsonld_description
    if not description:
        meta = tree.css_first('meta[name="description"]')
        description = meta.attributes.get("content") if meta is not None else None
        if description:
            description = description.strip() or None

    # --- Additional info fields ---
    region = _additional_info(tree, "Region")
    audience_raw = _additional_info(tree, "Audience")
    instructors = _additional_info(tree, "Instructors")

    return {
        "title": title,
        "starts_at_tuple": starts_tuple,
        "ends_at_tuple": ends_tuple,
        "location": location,
        "avdc_category": category_text,
        "event_type": type_text,
        "register_url": register_url,
        "description": description,
        "region": region,
        "audience": audience_raw,
        "instructors": instructors,
    }
# ---------- Mapping helpers ----------

def _map_event_type_to_format(event_type: str | None) -> str | None:
    """Map AVDC's event-type label to our listings.format slug.

    Webinar -> live (online live event)
    Lecture / Lecture and Wet Lab / Wet Lab -> live (in-person scheduled event)
    Anything else -> None
    """
    if not event_type:
        return None
    lowered = event_type.lower()
    if "webinar" in lowered:
        return "live"
    if "lecture" in lowered or "wet lab" in lowered or "lab" in lowered:
        return "live"
    return None


def _map_audience(audience_raw: str | None) -> str | None:
    """Map AVDC's free-text audience to our 'vets' / 'techs' / 'vets and techs'."""
    if not audience_raw:
        return None
    lowered = audience_raw.lower()
    has_vets = (
        "veterinarian" in lowered or "dvm" in lowered
        or "diplomate" in lowered or "resident" in lowered
    )
    has_techs = (
        "technician" in lowered or "tech " in lowered
        or "nurse" in lowered or "rvt" in lowered or "lvt" in lowered
        or "cvt" in lowered
    )
    if has_vets and has_techs:
        return "vets and techs"
    if has_vets:
        return "vets"
    if has_techs:
        return "techs"
    return None


# ---------- Mapping to RawListing ----------

def _detail_to_raw_listing(
    fields: dict, source_url: str
) -> RawListing | None:
    title = (fields.get("title") or "").strip()
    if not title:
        return None

    from datetime import date as _date  # local import — avoid module-level coupling
    starts_at = None
    ends_at = None
    s = fields.get("starts_at_tuple")
    e = fields.get("ends_at_tuple")
    if s is not None:
        try:
            starts_at = _date(*s)
        except ValueError:
            starts_at = None
    if e is not None:
        try:
            ends_at = _date(*e)
        except ValueError:
            ends_at = None

    description_parts: list[str] = []
    if fields.get("description"):
        description_parts.append(fields["description"])
    if fields.get("location"):
        description_parts.append(f"Location: {fields['location']}")
    if fields.get("event_type"):
        description_parts.append(f"Type: {fields['event_type']}")
    description = " | ".join(description_parts) if description_parts else None

    credit_hours = _parse_credit_hours(fields.get("description") or "")
    fmt = _map_event_type_to_format(fields.get("event_type"))
    audience = _map_audience(fields.get("audience"))

    # AVDC events are RACE-approved by virtue of being run by AVDC, but we don't
    # want to assert that without seeing the exact wording. Leave as None — the
    # tagger / a follow-up review can confirm.
    race_approved: bool | None = None

    return RawListing(
        source_slug=AvdcEventsScraper.SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider=AvdcEventsScraper.PROVIDER_NAME,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        format=fmt,
        cost=None,
        race_approved=race_approved,
        credit_hours=credit_hours,
        audience=audience,
        registration_url=fields.get("register_url"),
        presenter=fields.get("instructors"),
    )


# ---- The scraper class itself ----

class AvdcEventsScraper(BaseScraper):
    SOURCE_SLUG = "avdc_events"
    PROVIDER_NAME = "American Veterinary Dental College"
    LISTINGS_URL = f"{AVDC_BASE}/events/"
    REQUEST_DELAY = 0.5  # polite — ~5 detail fetches per run today, may grow

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        urls = _extract_event_links(listings_html)
        log.info("avdc_events_found", count=len(urls))

        for i, url in enumerate(urls, start=1):
            try:
                detail_html = self.fetch(url, client)
                fields = _extract_detail_fields(detail_html)
            except httpx.HTTPError as e:
                log.warning(
                    "avdc_detail_fetch_failed",
                    n=i,
                    url=url,
                    error=str(e),
                )
                continue

            listing = _detail_to_raw_listing(fields, source_url=url)
            if listing is None:
                log.info("avdc_skipped_empty_title", n=i, url=url)
                continue

            log.info(
                "avdc_event_parsed",
                n=i,
                title=listing.title,
                starts_at=str(listing.starts_at),
                location=fields.get("location"),
                credit_hours=str(listing.credit_hours) if listing.credit_hours else None,
                audience=listing.audience,
                avdc_category=fields.get("avdc_category"),
            )
            yield listing


if __name__ == "__main__":
    AvdcEventsScraper().run()   