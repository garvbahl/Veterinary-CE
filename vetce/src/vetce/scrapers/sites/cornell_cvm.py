"""Scraper for Cornell College of Veterinary Medicine CE conferences.

Source page: vet.cornell.edu/education/educational-support-services/continuing-education

Structure:
- A Drupal CMS page with a flat sequence of <h3> + <ul> pairs inside
  div.field-item.even.
- Each conference is one <h3> followed by a <ul> with labeled <li> bullets:
    <li><strong>Website:</strong> link</li>
    <li><strong>Registration:</strong> status</li>
    <li><strong>Dates:</strong> May 16-17, 2026</li>
    <li><strong>Location:</strong> Hybrid Event: Weill Cornell, NYC & Live Online</li>
    <li><strong>CE Credits:</strong> Pending approval for 8 CE credits for veterinarians</li>
- The "2026 Conferences" section is bounded by <h2 class="promote"> headings;
  we only consume <h3>s between the first such h2 and the next one.

This is a third extraction pattern: text-heavy labeled lists. No JSON,
no per-element class names — we walk siblings and parse "Label: Value" bullets.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.config import settings
from vetce.logging import log
from vetce.pipeline.ingest import run_ingest
from vetce.scrapers.types import RawListing

SOURCE_SLUG = "cornell_cvm_conferences"
LISTINGS_URL = (
    "https://www.vet.cornell.edu/education/"
    "educational-support-services/continuing-education"
)
SECTION_HEADER_TEXT = "2026 Conferences"  # update yearly

# ---------- Date parsing ----------

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "May 16-17, 2026" or "May 16 - 17, 2026"
_RE_SAME_MONTH_RANGE = re.compile(
    r"^([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),\s*(\d{4})\b",
    re.IGNORECASE,
)
# "May 16, 2026"  (single day)
_RE_SINGLE_DAY = re.compile(
    r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b",
    re.IGNORECASE,
)
# "December 30, 2026 - January 2, 2027"  (cross-month / cross-year)
_RE_CROSS_MONTH = re.compile(
    r"^([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})?\s*[-–]\s*"
    r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b",
    re.IGNORECASE,
)


def _parse_dates(text: str) -> tuple[date | None, date | None]:
    """Parse a Cornell-style date string into (starts_at, ends_at).

    Returns (None, None) on any unparseable input (with a warning).
    """
    if not text:
        return (None, None)

    cleaned = text.strip().replace("–", "-").replace("—", "-")

    # Try cross-month/year first since it's more specific
    m = _RE_CROSS_MONTH.match(cleaned)
    if m:
        start_month, start_day, start_year, end_month, end_day, end_year = m.groups()
        start_year = start_year or end_year  # if start year missing, use end year
        try:
            start = date(int(start_year), _MONTHS[start_month.lower()], int(start_day))
            end = date(int(end_year), _MONTHS[end_month.lower()], int(end_day))
            return (start, end)
        except (KeyError, ValueError) as e:
            log.warning("cornell_date_parse_failed", text=text, error=str(e))
            return (None, None)

    m = _RE_SAME_MONTH_RANGE.match(cleaned)
    if m:
        month, start_day, end_day, year = m.groups()
        try:
            start = date(int(year), _MONTHS[month.lower()], int(start_day))
            end = date(int(year), _MONTHS[month.lower()], int(end_day))
            return (start, end)
        except (KeyError, ValueError) as e:
            log.warning("cornell_date_parse_failed", text=text, error=str(e))
            return (None, None)

    m = _RE_SINGLE_DAY.match(cleaned)
    if m:
        month, day, year = m.groups()
        try:
            d = date(int(year), _MONTHS[month.lower()], int(day))
            return (d, d)
        except (KeyError, ValueError) as e:
            log.warning("cornell_date_parse_failed", text=text, error=str(e))
            return (None, None)

    log.warning("cornell_date_unparseable", text=text)
    return (None, None)


# ---------- CE credits / audience parsing ----------

# "Pending approval for 8 CE credits for veterinarians"
# "15.5 CE credits for veterinarians and veterinary technicians"
# "up to 21 credits during the live event"
_RE_CREDITS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:CE\s+)?credits?", re.IGNORECASE)


def _parse_credits_and_audience(text: str) -> tuple[float | None, str | None]:
    """Extract credit hours and audience from a CE Credits bullet."""
    if not text:
        return (None, None)

    credits = None
    m = _RE_CREDITS.search(text)
    if m:
        try:
            credits = float(m.group(1))
        except ValueError:
            log.warning("cornell_credits_parse_failed", text=text)

    lowered = text.lower()
    audience = None
    has_vets = "veterinarian" in lowered
    has_techs = "technician" in lowered or "nurse" in lowered
    if has_vets and has_techs:
        audience = "vets and techs"
    elif has_vets:
        audience = "vets"
    elif has_techs:
        audience = "techs"

    return (credits, audience)


# ---------- Format parsing ----------

def _parse_format(location_text: str) -> str | None:
    """Infer 'live' / 'on_demand' / 'hybrid' from a Location string."""
    if not location_text:
        return None
    lowered = location_text.lower()
    if "hybrid" in lowered:
        return "hybrid"
    if "on-demand" in lowered or "on demand" in lowered:
        return "on_demand"
    if "live online" in lowered or "in-person" in lowered or "in person" in lowered:
        return "live"
    return None


# ---------- HTML walking ----------

def _bullets_to_fields(ul: Node) -> dict[str, str]:
    """Given a <ul>, return {label: value} for each <li> shaped 'Label: Value'."""
    fields: dict[str, str] = {}
    for li in ul.css("li"):
        text = li.text(separator=" ", strip=True)
        if ":" not in text:
            continue
        label, _, value = text.partition(":")
        fields[label.strip().lower()] = value.strip()
    return fields


def _first_link(ul: Node) -> str | None:
    """Get the first href inside a <ul>, if any. Used as registration_url."""
    a = ul.css_first("a[href]")
    return a.attributes.get("href") if a else None


def _extract_conferences(html: str) -> list[dict]:
    """Walk the page and return one dict per conference in the target section."""
    tree = HTMLParser(html)

    # Find the section anchor: an <h2> whose text contains "2026 Conferences"
    section_h2: Node | None = None
    for h2 in tree.css("h2"):
        if SECTION_HEADER_TEXT.lower() in h2.text(strip=True).lower():
            section_h2 = h2
            break
    if section_h2 is None:
        raise ValueError(f"Could not find section header {SECTION_HEADER_TEXT!r}")

    # Walk forward through siblings collecting <h3> + next <ul> pairs.
    # Stop when we hit another <h2> (next section).
    conferences: list[dict] = []
    current_title: str | None = None

    node = section_h2.next
    while node is not None:
        tag = node.tag
        if tag == "h2":
            break  # entered next section
        if tag == "h3":
            current_title = node.text(strip=True)
        elif tag == "ul" and current_title:
            fields = _bullets_to_fields(node)
            # A real conference has at least a "dates:" bullet. Anything else
            # is a non-conference subsection (e.g., the Sim Lab link block).
            if "dates" not in fields:
                log.info("cornell_skipped_non_conference",
                         title=current_title)
                current_title = None
                node = node.next
                continue
            registration_url = _first_link(node)
            conferences.append({
                "title": current_title,
                "fields": fields,
                "registration_url": registration_url,
            })
            current_title = None  # consumed
        node = node.next

    return conferences


# ---------- Mapping to RawListing ----------

def _conference_to_raw_listing(conf: dict) -> RawListing | None:
    title = conf.get("title", "").strip()
    if not title:
        return None  # skip empty <h3>s

    fields = conf.get("fields", {})
    starts_at, ends_at = _parse_dates(fields.get("dates", ""))
    credit_hours, audience = _parse_credits_and_audience(fields.get("ce credits", ""))
    fmt = _parse_format(fields.get("location", ""))

    description_parts = []
    if fields.get("location"):
        description_parts.append(f"Location: {fields['location']}")
    if fields.get("registration"):
        description_parts.append(f"Registration: {fields['registration']}")
    if fields.get("ce credits"):
        description_parts.append(f"CE Credits: {fields['ce credits']}")
    description = "\n".join(description_parts) if description_parts else None

    # Use Cornell page URL + slugified title as the unique source_url.
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    source_url = f"{LISTINGS_URL}#{slug}"

    return RawListing(
        source_slug=SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider="Cornell CVM",
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        format=fmt,
        cost=None,  # not explicitly stated; honest absence
        race_approved=None,  # not stated on hub page
        credit_hours=credit_hours,
        audience=audience,
        registration_url=conf.get("registration_url"),
    )


# ---------- Entry point ----------

def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.user_agent},
        timeout=20.0,
        follow_redirects=True,
    )


def scrape() -> Iterable[RawListing]:
    with _client() as client:
        log.info("fetch", url=LISTINGS_URL)
        resp = client.get(LISTINGS_URL)
        resp.raise_for_status()
        html = resp.text

    conferences = _extract_conferences(html)
    log.info("cornell_conferences_found", count=len(conferences))

    for i, conf in enumerate(conferences, start=1):
        listing = _conference_to_raw_listing(conf)
        if listing is None:
            log.info("cornell_skipped_empty_title", n=i)
            continue
        log.info(
            "cornell_conference_parsed",
            n=i,
            title=listing.title,
            starts_at=str(listing.starts_at),
            credits=listing.credit_hours,
            audience=listing.audience,
        )
        yield listing


if __name__ == "__main__":
    from vetce.logging import configure_logging
    configure_logging()
    counts = run_ingest(scrape, source_slug=SOURCE_SLUG)
    print(f"\nDone: {counts}")