"""Scraper for Veterinary Dental Specialties (vdspets.com) -- Dr. Brook Niemiec.

VDS runs hands-on dental wet labs and CE lectures across ~14 US locations.
The site is WordPress + WooCommerce with the public Store API wide open:
    https://www.vdspets.com/wp-json/wc/store/v1/products?per_page=100&page=N
No auth. Returns all products as JSON, paginated.

Key facts about the data:
- Courses are in the "class" category (slug "class"). Other categories
  (Instruments & Kits, Sharpening Services) are merch -- skipped.
- The Store API returns the ENTIRE historical catalog (~97 class products,
  mostly past 2023-2025 events). We filter to UPCOMING dates only.
- WooCommerce has no native event-date field, so the date lives in the
  product `name` as "(M/D/YY)" / "M/D/YY" / ranges, with a "DATES:" line in
  the `description` as fallback.
- prices.price is in minor units (cents): "159900" -> $1,599.00. price 0 = Free.
- CE hours + RACE live in the `description` text ("8 hours of CE through RACE"
  / "8 units of CE"). Not in structured fields (attributes is empty).
- "Banfield Only" products are exclusive to Banfield employees (public users
  cannot register) -- skipped.

Architecture:
- Paginate the Store API until a page returns fewer than per_page.
- Keep products where: category includes "class", a date parses, that date is
  today-or-future, it's not Banfield-only, and CE hours parse from the
  description (the CE-hours requirement also filters out non-CE social events
  like dinners and open houses).
- One RawListing per product. source_url = permalink.
"""
from __future__ import annotations

import html as html_module
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

import httpx

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


VDS_BASE = "https://www.vdspets.com"
STORE_API = f"{VDS_BASE}/wp-json/wc/store/v1/products"
PER_PAGE = 100


# ---------- text helpers ----------

def _strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ---------- date parsing ----------

# Ordered patterns. Each returns (start_date, end_date).
# Years are 2-digit (YY -> 20YY) or 4-digit.

def _yy(year: str) -> int:
    y = int(year)
    return 2000 + y if y < 100 else y


def _parse_date_from_text(text: str) -> tuple[date, date] | None:
    """Extract a (start, end) date from a product name or 'DATES:' string.

    Handles, in priority order:
      - "M/D-D/YY"      range within one month   e.g. 6/20-6/21/26
      - "M/D-M/D/YY"    range across months      e.g. 3/7-3/9/26 (same year)
      - "M/D/YY" or "MM/DD/YYYY"  single day      e.g. 8/29/26, 04/29/26
      - "M-D-YY"        dash single day          e.g. 10-20-24
    Returns None if nothing parseable.
    """
    if not text:
        return None

    # Range within one month: 6/20-6/21/26  OR  6/20-21/26
    m = re.search(
        r"\b(\d{1,2})/(\d{1,2})\s*-\s*(?:(\d{1,2})/)?(\d{1,2})/(\d{2,4})\b", text
    )
    if m:
        mon1, day1 = int(m.group(1)), int(m.group(2))
        mon2 = int(m.group(3)) if m.group(3) else mon1
        day2 = int(m.group(4))
        year = _yy(m.group(5))
        try:
            start = date(year, mon1, day1)
            end = date(year, mon2, day2)
            if end >= start:
                return (start, end)
        except ValueError:
            pass

    # Single day: 8/29/26 or 04/29/2026
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", text)
    if m:
        try:
            d = date(_yy(m.group(3)), int(m.group(1)), int(m.group(2)))
            return (d, d)
        except ValueError:
            pass

    # Dash single day: 10-20-24
    m = re.search(r"\b(\d{1,2})-(\d{1,2})-(\d{2,4})\b", text)
    if m:
        try:
            d = date(_yy(m.group(3)), int(m.group(1)), int(m.group(2)))
            return (d, d)
        except ValueError:
            pass

    return None


def _extract_dates(name: str, description_text: str) -> tuple[date, date] | None:
    """Try the name first (most reliable), then the 'DATES:' line in the body."""
    d = _parse_date_from_text(name)
    if d:
        return d
    # Fallback: look for a "DATES:" segment in the description.
    m = re.search(r"DATES?\s*:?\s*(.+?)(?:LOCATION|COST|CE\b|$)", description_text,
                  re.IGNORECASE)
    if m:
        # Try the M/D/YY style first; otherwise a spelled-out date.
        d = _parse_date_from_text(m.group(1))
        if d:
            return d
        spelled = _parse_spelled_date(m.group(1))
        if spelled:
            return (spelled, spelled)
    # Last resort: a spelled-out date anywhere ("August 29, 2026").
    spelled = _parse_spelled_date(description_text)
    if spelled:
        return (spelled, spelled)
    return None


_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def _parse_spelled_date(text: str) -> date | None:
    m = re.search(r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})\b",
                  text, re.IGNORECASE)
    if not m:
        return None
    try:
        return date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    except ValueError:
        return None


# ---------- CE hours ----------

_RE_CE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:hours?|units?)\s+of\s+CE"
    r"|approved\s+for\s+(\d+(?:\.\d+)?)\s*hours?"
    r"|(\d+(?:\.\d+)?)\s*(?:hours?|units?)\s+CE",
    re.IGNORECASE,
)


def _parse_ce_hours(text: str) -> tuple[Decimal | None, bool]:
    """Return (credit_hours, race_approved). RACE is True if 'RACE' appears."""
    race = "race" in text.lower()
    m = _RE_CE.search(text)
    if not m:
        return (None, race)
    val = next((g for g in m.groups() if g), None)
    if val is None:
        return (None, race)
    try:
        h = Decimal(val)
        return (h if h > 0 else None, race)
    except (ValueError, ArithmeticError):
        return (None, race)


# ---------- cost / audience / presenter / location ----------

def _parse_cost(prices: dict[str, Any]) -> str | None:
    raw = prices.get("price")
    if raw is None:
        return None
    try:
        cents = int(raw)
    except (ValueError, TypeError):
        return None
    if cents == 0:
        return "Free"
    minor = int(prices.get("currency_minor_unit", 2))
    dollars = Decimal(cents) / (Decimal(10) ** minor)
    # Format without trailing .00 noise but keep cents if present.
    if dollars == dollars.to_integral_value():
        return f"${int(dollars):,}"
    return f"${dollars:,.2f}"


def _parse_audience(text: str) -> str | None:
    low = text.lower()
    has_vet = "veterinarian" in low or "vets" in low or " vet " in low
    has_tech = "technician" in low or "techs" in low or " tech " in low
    if "vets only" in low or "veterinarians only" in low:
        return "vets"
    if has_vet and has_tech:
        return "vets and techs"
    if has_tech and not has_vet:
        return "techs"
    if has_vet:
        return "vets"
    return None


# Capture a person's name after "Taught by" / "Instructor:", stopping at the
# first non-name token. Names are 2-4 capitalized words, optionally credentialed
# (RVT, VTS, DVM, etc.) in parens or trailing.
_RE_PRESENTER = re.compile(
    r"(?:Taught by|Instructor)\s*:?\s*"
    r"((?:Dr\.\s*)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
)

# Known trailing words that indicate the name capture overran into prose.
_PRESENTER_STOPWORDS = {
    "the", "description", "join", "under", "attendees", "this", "we",
    "basic", "advanced", "level",
}


def _parse_presenter(text: str) -> str | None:
    m = _RE_PRESENTER.search(text)
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        # Trim any trailing stopword the greedy match may have pulled in.
        parts = name.split()
        while parts and parts[-1].lower() in _PRESENTER_STOPWORDS:
            parts.pop()
        name = " ".join(parts)
        if name:
            return name
    if "niemiec" in text.lower():
        return "Dr. Brook Niemiec"
    return None


def _parse_location(name: str, text: str) -> str | None:
    # The name often leads with "CITY |"; use that.
    m = re.match(r"\s*([A-Za-z .]+?)\s*\|", name)
    if m:
        loc = m.group(1).strip()
        if loc and loc.lower() not in ("level i", "level ii", "level i & ii"):
            return loc.title()
    # Else a "LOCATION:" line.
    m = re.search(r"LOCATION\s*:?\s*(.+?)(?:COST|CE\b|QUESTIONS|LIMITED|$)",
                  text, re.IGNORECASE)
    if m:
        return _strip_html(m.group(1))[:120] or None
    return None


def _is_banfield(name: str, text: str) -> bool:
    return "banfield" in (name + " " + text).lower()


# ---------- the scraper ----------

class VdsPetsScraper(BaseScraper):
    SOURCE_SLUG = "vdspets"
    PROVIDER_NAME = "Veterinary Dental Specialties"
    LISTINGS_URL = STORE_API
    REQUEST_DELAY = 0.5
    MAX_PAGES = 10  # safety ceiling; ~97 class products -> 1-2 pages

    def make_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def list_pages(self) -> Iterable[str]:
        # Single entry; extract_listings paginates internally.
        yield f"{STORE_API}?per_page={PER_PAGE}&page=1"

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        import json

        today = date.today()
        kept = 0
        skipped_past = 0
        skipped_banfield = 0
        skipped_no_ce = 0
        skipped_no_date = 0

        page = 1
        first_payload = listings_html
        while page <= self.MAX_PAGES:
            if page == 1:
                raw = first_payload
            else:
                url = f"{STORE_API}?per_page={PER_PAGE}&page={page}"
                try:
                    raw = self.fetch(url, client)
                except httpx.HTTPError as e:
                    log.warning("vdspets_page_fetch_failed", page=page, error=str(e))
                    break

            try:
                products = json.loads(raw)
            except json.JSONDecodeError:
                log.warning("vdspets_bad_json", page=page)
                break

            if not isinstance(products, list) or not products:
                break

            for p in products:
                cats = {c.get("slug") for c in (p.get("categories") or [])}
                if "class" not in cats:
                    continue

                name = _strip_html(p.get("name"))
                body = _strip_html(p.get("description")) + " " + \
                    _strip_html(p.get("short_description"))

                if _is_banfield(name, body):
                    skipped_banfield += 1
                    continue

                dates = _extract_dates(name, body)
                if dates is None:
                    skipped_no_date += 1
                    log.info("vdspets_skip_no_date", name=name)
                    continue
                starts_at, ends_at = dates

                if ends_at < today:
                    skipped_past += 1
                    continue

                credit_hours, race = _parse_ce_hours(body)
                if credit_hours is None:
                    # No CE hours -> likely a social/dinner/open-house event,
                    # not a CE course. Skip.
                    skipped_no_ce += 1
                    log.info("vdspets_skip_no_ce", name=name)
                    continue

                cost = _parse_cost(p.get("prices") or {})
                presenter = _parse_presenter(body)
                audience = _parse_audience(body)
                location = _parse_location(name, body)
                permalink = p.get("permalink")

                description = _strip_html(p.get("short_description")) or None
                if location:
                    loc_note = f"Location: {location}."
                    description = f"{description} {loc_note}" if description else loc_note

                kept += 1
                log.info(
                    "vdspets_course_parsed",
                    name=name,
                    starts=str(starts_at),
                    ce=str(credit_hours),
                    cost=cost,
                    audience=audience,
                )

                yield RawListing(
                    source_slug=self.SOURCE_SLUG,
                    source_url=permalink,
                    title=name,
                    provider=self.PROVIDER_NAME,
                    description=description,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    format="live",
                    cost=cost,
                    race_approved=race,
                    credit_hours=credit_hours,
                    audience=audience,
                    registration_url=permalink,
                    presenter=presenter,
                )

            if len(products) < PER_PAGE:
                break
            page += 1

        log.info(
            "vdspets_summary",
            kept=kept,
            skipped_past=skipped_past,
            skipped_banfield=skipped_banfield,
            skipped_no_ce=skipped_no_ce,
            skipped_no_date=skipped_no_date,
        )


if __name__ == "__main__":
    VdsPetsScraper().run()