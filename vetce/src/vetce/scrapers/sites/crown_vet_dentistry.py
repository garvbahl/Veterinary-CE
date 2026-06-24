"""Scraper for Crown Veterinary Dental Specialists (crownvetdentistry.com).

Source page: crownvetdentistry.com/continuing-education/

Structure:
- WordPress site running the Divi theme. Each course is a Divi text module
  on a single static page. There's no calendar plugin, no REST API, no
  JSON-LD — just hand-written HTML.
- Each course block consists of:
    <div class="et_pb_text_inner">
        <h2 dir="auto">COURSE TITLE</h2>
        <p>
            <strong>DATE TEXT</strong><span> | </span>
            <strong>N Hours RACE CE</strong><span> | </span>
            <strong>$PRICE</strong>
        </p>
        <p>Description paragraph...</p>
        <ul><li>...</li></ul>
    </div>
- The audience footer ("This course is for veterinarians only" /
  "This course is for Veterinarians, Veterinary Technicians & Assistants")
  lives in a separate <div class="et_pb_text_inner"><em>...</em></div>
  later in the page. We collect all of these and match each course to the
  next audience-italic that appears after its <h2>.

KNOWN FRAGILITY:
- Dates are free text ("Sep 6th OR Sep 7th", "Oct 18 & 19th"). Year is NOT
  written anywhere on the page. We infer year using a "if month already
  passed, assume next year" heuristic.
- A course offered on two alternate dates ("Sep 6th OR Sep 7th") emits TWO
  listings, one per date.
- A course spanning two consecutive days ("Oct 18 & 19th") emits ONE listing
  with start/end set.
- Source URLs are faked with #hash fragments because the entire catalog
  lives at one URL. This is hacky but necessary for our dedup key.

Expect this scraper to need a patch when Crown changes their HTML or date
format. The CEO has accepted that maintenance cost.
"""
from __future__ import annotations

import html as html_module
import re
from datetime import date
from decimal import Decimal
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


CROWN_BASE = "https://crownvetdentistry.com"
LISTINGS_PATH = "/continuing-education/"


# ---------- Date parsing ----------

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Matches "Sep 6th", "September 6", "Sep 6", etc.
_RE_MONTH_DAY = re.compile(
    r"\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|"
    r"jul|july|aug|august|sep|sept|september|oct|october|nov|november|"
    r"dec|december)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)


def _infer_year(month: int, day: int) -> int:
    """If the given month/day already passed this year, return next year.
    Otherwise return this year.

    Crown's page doesn't include the year, and they keep upcoming events
    listed. So a "Sep 6th" entry seen in October must mean next September.
    """
    from datetime import date as _date  # local
    today = _date.today()
    try:
        proposed = _date(today.year, month, day)
    except ValueError:
        return today.year
    if proposed < today:
        return today.year + 1
    return today.year


def _extract_dates(text: str) -> list[tuple[date, date]]:
    """Pull all (start, end) date pairs from a date phrase.

    Returns a list because "X OR Y" yields two separate dates; the scraper
    emits one listing per pair.

    Patterns handled:
    - "Sep 6th"                  -> [(Sep 6, Sep 6)]
    - "Sep 6th OR Sep 7th"       -> [(Sep 6, Sep 6), (Sep 7, Sep 7)]
    - "Oct 18 & 19th"            -> [(Oct 18, Oct 19)]
    - "Oct 18 & Oct 19th"        -> [(Oct 18, Oct 19)]
    - "Dec 13th AM with Dec 13th PM" -> [(Dec 13, Dec 13)] (dedup'd)
    """
    if not text:
        return []

    matches = list(_RE_MONTH_DAY.finditer(text))
    if not matches:
        return []

    # Build (month, day) pairs, carrying month across when text only repeats day.
    parsed: list[tuple[int, int]] = []
    for m in matches:
        month_text = m.group(1).lower().rstrip(".")
        month = _MONTHS.get(month_text)
        if month is None:
            continue
        day = int(m.group(2))
        parsed.append((month, day))

    # Handle bare "& 19th" where the second match might be missing — fallback:
    # find "& <number>(st|nd|rd|th)?" tokens between adjacent matches.
    _RE_LONE_DAY = re.compile(r"&\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE)
    for lone in _RE_LONE_DAY.finditer(text):
        day = int(lone.group(1))
        # Pair with the most recent month seen before this position.
        before = [
            (mo, d) for (mo, d) in parsed
            if text.lower().find(f"{day}", lone.start()) >= 0
        ]
        # Pull the most recently matched month from `matches`.
        prev_month: int | None = None
        for mt in matches:
            if mt.end() < lone.start():
                prev_month = _MONTHS.get(mt.group(1).lower().rstrip("."))
        if prev_month is not None and (prev_month, day) not in parsed:
            parsed.append((prev_month, day))

    # Dedup while preserving order.
    seen: set[tuple[int, int]] = set()
    deduped: list[tuple[int, int]] = []
    for pair in parsed:
        if pair in seen:
            continue
        seen.add(pair)
        deduped.append(pair)

    if not deduped:
        return []

    # Decide how to pair up the dates.
    text_lower = text.lower()
    is_range = " & " in text_lower or "through" in text_lower or "-" in text_lower
    is_alternates = " or " in text_lower

    pairs: list[tuple[date, date]] = []
    if is_range and len(deduped) >= 2 and not is_alternates:
        # Treat first as start, last as end. Multi-day single event.
        start_m, start_d = deduped[0]
        end_m, end_d = deduped[-1]
        try:
            start_date = date(_infer_year(start_m, start_d), start_m, start_d)
            end_date = date(_infer_year(end_m, end_d), end_m, end_d)
            pairs.append((start_date, end_date))
        except ValueError:
            pass
    else:
        # Each date is a separate scheduling option ("X OR Y") or a lone date.
        for m, d in deduped:
            try:
                dt = date(_infer_year(m, d), m, d)
                pairs.append((dt, dt))
            except ValueError:
                continue

    return pairs


# ---------- Metadata line parsing ----------

# Crown's metadata line: "Sep 6th OR Sep 7th | 4 Hours RACE CE | $275"
_RE_HOURS = re.compile(r"(\d+(?:\.\d+)?)\s*hours?\b", re.IGNORECASE)
_RE_RACE = re.compile(r"\brace\b", re.IGNORECASE)
_RE_PRICE = re.compile(r"\$\s*[\d,]+(?:\.\d{2})?")


def _parse_credit_hours(text: str) -> Decimal | None:
    m = _RE_HOURS.search(text or "")
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except ValueError:
        return None


def _parse_price(text: str) -> str | None:
    m = _RE_PRICE.search(text or "")
    return m.group(0).replace(" ", "") if m else None


def _parse_race(text: str) -> bool | None:
    if not text:
        return None
    return True if _RE_RACE.search(text) else None


# ---------- Audience parsing ----------

def _parse_audience(footer_text: str | None) -> str | None:
    if not footer_text:
        return None
    lowered = footer_text.lower()
    has_techs = "technician" in lowered or "assistant" in lowered
    has_vets = "veterinarian" in lowered
    if has_techs and has_vets:
        return "vets and techs"
    if has_vets:
        return "vets"
    if has_techs:
        return "techs"
    return None


# ---------- HTML helpers ----------

def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def _slugify(text: str) -> str:
    """Build a URL-safe slug from a title for fake source_url fragments."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "course"


# ---------- Course extraction ----------

def _find_course_blocks(tree: HTMLParser) -> list[Node]:
    """Find each <div class='et_pb_text_inner'> whose direct child is an <h2>.

    Skips inners with no <h2> (those are descriptions, audience footers, etc.).
    """
    blocks: list[Node] = []
    for inner in tree.css("div.et_pb_text_inner"):
        h2 = inner.css_first("h2")
        if h2 is None:
            continue
        title_text = _clean(h2.text())
        if not title_text:
            continue
        # Skip headers that aren't actually courses (e.g., "Get In Touch",
        # "Questions?"). Courses on Crown's page are written in ALL CAPS.
        if title_text != title_text.upper():
            continue
        blocks.append(inner)
    return blocks


def _find_audience_footers(tree: HTMLParser) -> list[tuple[int, str]]:
    """Find all 'This course is for ...' italic footers with their DOM position.

    Returns a list of (position_index, text) ordered by appearance. Position
    is the cumulative index of the inner div in document order. We use that
    to match each course block to the NEAREST footer that comes AFTER it.
    """
    footers: list[tuple[int, str]] = []
    inners = tree.css("div.et_pb_text_inner")
    for idx, inner in enumerate(inners):
        em = inner.css_first("em")
        if em is None:
            continue
        text = _clean(em.text())
        if "this course is for" in text.lower():
            footers.append((idx, text))
    return footers


def _match_audience(
    course_idx: int, footers: list[tuple[int, str]]
) -> str | None:
    """Find the first audience footer at or after the given course index."""
    for fidx, ftext in footers:
        if fidx >= course_idx:
            return _parse_audience(ftext)
    return None


# ---------- Course block → RawListing(s) ----------

def _block_to_listings(
    inner: Node, course_idx: int, footers: list[tuple[int, str]]
) -> list[RawListing]:
    h2 = inner.css_first("h2")
    if h2 is None:
        return []
    title = _clean(h2.text())
    if not title:
        return []

    # The metadata <p> is the first <p> inside the inner that contains
    # at least one <strong>. The description is everything after.
    paragraphs = inner.css("p")
    meta_text: str | None = None
    description_parts: list[str] = []
    for p in paragraphs:
        if meta_text is None and p.css_first("strong") is not None:
            meta_text = _clean(p.text())
            continue
        text = _clean(p.text())
        if text:
            description_parts.append(text)

    # Bullet list, if present.
    for ul in inner.css("ul"):
        items = [_clean(li.text()) for li in ul.css("li") if _clean(li.text())]
        if items:
            description_parts.append("Topics: " + "; ".join(items))

    description = " | ".join(description_parts) or None

    # Parse the metadata line.
    credit_hours = _parse_credit_hours(meta_text)
    cost = _parse_price(meta_text)
    race_approved = _parse_race(meta_text)
    dates = _extract_dates(meta_text or "")

    audience = _match_audience(course_idx, footers)

    # Source URL — fake unique fragments so each (course, date) is its own row.
    slug = _slugify(title)
    base_url = f"{CROWN_BASE}{LISTINGS_PATH}"

    listings: list[RawListing] = []
    if not dates:
        # Couldn't parse a date — still emit a listing without start_at so
        # it's at least visible in admin and editable manually.
        listings.append(
            RawListing(
                source_slug=CrownVetDentistryScraper.SOURCE_SLUG,
                source_url=f"{base_url}#{slug}",
                title=title,
                provider=CrownVetDentistryScraper.PROVIDER_NAME,
                description=description,
                starts_at=None,
                ends_at=None,
                format="live",
                cost=cost,
                race_approved=race_approved,
                credit_hours=credit_hours,
                audience=audience,
                registration_url=base_url,
                presenter=None,
            )
        )
        log.warning("crown_no_date_parsed", title=title, meta=meta_text)
        return listings

    for starts_at, ends_at in dates:
        # If a course has multiple date options, append the date to the
        # fragment so each gets a unique source_url.
        date_suffix = f"-{starts_at.isoformat()}"
        listings.append(
            RawListing(
                source_slug=CrownVetDentistryScraper.SOURCE_SLUG,
                source_url=f"{base_url}#{slug}{date_suffix}",
                title=title,
                provider=CrownVetDentistryScraper.PROVIDER_NAME,
                description=description,
                starts_at=starts_at,
                ends_at=ends_at,
                format="live",
                cost=cost,
                race_approved=race_approved,
                credit_hours=credit_hours,
                audience=audience,
                registration_url=base_url,
                presenter=None,
            )
        )
    return listings


# ---------- The scraper class ----------

class CrownVetDentistryScraper(BaseScraper):
    SOURCE_SLUG = "crown_vet_dentistry"
    PROVIDER_NAME = "Crown Veterinary Dental Specialists"
    LISTINGS_URL = f"{CROWN_BASE}{LISTINGS_PATH}"
    REQUEST_DELAY = 0.0  # single fetch

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        tree = HTMLParser(listings_html)

        # Build an inner-div index so we can locate audience footers relative
        # to course blocks in document order.
        all_inners = tree.css("div.et_pb_text_inner")
        inner_index: dict[int, int] = {id(n): i for i, n in enumerate(all_inners)}

        footers = _find_audience_footers(tree)
        course_blocks = _find_course_blocks(tree)

        log.info("crown_courses_found", count=len(course_blocks))

        total_listings = 0
        for inner in course_blocks:
            idx = inner_index.get(id(inner), 0)
            listings = _block_to_listings(inner, idx, footers)
            for listing in listings:
                total_listings += 1
                log.info(
                    "crown_listing_parsed",
                    title=listing.title,
                    starts_at=str(listing.starts_at) if listing.starts_at else None,
                    credit_hours=str(listing.credit_hours) if listing.credit_hours else None,
                    cost=listing.cost,
                    audience=listing.audience,
                )
                yield listing

        log.info("crown_total_listings", count=total_listings)


if __name__ == "__main__":
    CrownVetDentistryScraper().run()