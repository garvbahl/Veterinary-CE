"""Scraper for Vet Dental Classes (vetdentalclasses.com).

Dr. Patrick Vall, DAVDC -- Animal Dental Care & Oral Surgery, Colorado Springs.
A small, fixed catalog of 2-day lecture + wet-lab dental courses. Each course
is a hand-built WordPress page (NOT a WooCommerce product loop), discoverable
from the "Courses" nav dropdown. Each page lists multiple scheduled weekend
dates in an Events Manager table.

NOTE ON RATE-LIMITING: this site has previously returned 429 to automated
fetches. We use a generous REQUEST_DELAY and fetch only ~5 pages per run
(the home page to discover course URLs, then each course page).

Architecture (Option C -- one listing per COURSE, all dates in description):
- Fetch the listings page, parse the "Courses" nav menu to discover course
  page URLs (so a new course auto-appears without code changes).
- For each course page: extract title, description (JSON-LD), CE hours + RACE
  (from "RACE approved for N hours"), price ("Individual Price $X"), and ALL
  scheduled dates (from the Events Manager date table).
- Emit ONE RawListing per course. starts_at = nearest upcoming date; the full
  date list is appended to the description so users see every offering.
- source_url = the clean course-page URL (no hash hacks needed).

Per-course audience differs: most are "for veterinarians"; the "Bite-sized
Wisdom" course is explicitly for veterinary technicians. We detect this from
the page text.
"""
from __future__ import annotations

import html as html_module
import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


VDC_BASE = "https://vetdentalclasses.com"


# ---------- Field parsers ----------

_RE_RACE_HOURS = re.compile(
    r"RACE\s+approved\s+for\s+(\d+(?:\.\d+)?)\s+hours?",
    re.IGNORECASE,
)
_RE_PRICE = re.compile(r"Individual\s+Price\s+(\$[\d,]+(?:\.\d{2})?)", re.IGNORECASE)
# Matches "09/17/2026 - 09/18/2026"
_RE_DATE_RANGE = re.compile(
    r"(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})"
)
# Single-day fallback "09/17/2026"
_RE_DATE_SINGLE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

_MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def _parse_credit_hours(page_text: str) -> tuple[Decimal | None, bool | None]:
    m = _RE_RACE_HOURS.search(page_text)
    if not m:
        return (None, None)
    try:
        return (Decimal(m.group(1)), True)
    except (ValueError, ArithmeticError):
        return (None, True)


def _parse_price(page_text: str) -> str | None:
    m = _RE_PRICE.search(page_text)
    return m.group(1) if m else None


def _parse_description(tree: HTMLParser) -> str | None:
    """Pull the WebPage description from the Yoast JSON-LD graph."""
    for script in tree.css('script.yoast-schema-graph'):
        raw = script.text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in data.get("@graph", []):
            if node.get("@type") == "WebPage" and node.get("description"):
                return _clean(node["description"])
    return None


def _parse_audience(page_text: str) -> str | None:
    low = page_text.lower()
    has_tech = "technician" in low
    # "for veterinarians" / "veterinarians seeking"
    has_vet = "veterinarian" in low
    # The Bite-sized course is tech-focused; if "for veterinary technicians"
    # appears prominently and vets don't, call it techs.
    if "for veterinary technicians" in low and "veterinarians seeking" not in low:
        return "techs"
    if has_vet and has_tech:
        return "vets and techs"
    if has_vet:
        return "vets"
    if has_tech:
        return "techs"
    return None


def _parse_all_dates(tree: HTMLParser) -> list[tuple[date, date]]:
    """Extract every scheduled (start, end) date pair from the Events Manager
    date table (<td data-label="Date/Time">), plus any single calendar entry.

    Deduped and sorted ascending.
    """
    pairs: set[tuple[date, date]] = set()

    # Primary source: the date/time table cells.
    for td in tree.css('td[data-label="Date/Time"]'):
        text = td.text(separator=" ")
        m = _RE_DATE_RANGE.search(text)
        if m:
            try:
                start = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                end = date(int(m.group(6)), int(m.group(4)), int(m.group(5)))
                pairs.add((start, end))
                continue
            except ValueError:
                pass
        # Single-day fallback.
        sm = _RE_DATE_SINGLE.search(text)
        if sm:
            try:
                d = date(int(sm.group(3)), int(sm.group(1)), int(sm.group(2)))
                pairs.add((d, d))
            except ValueError:
                pass

    # Secondary: any "MM/DD/YYYY - MM/DD/YYYY" in event-meta lines the table
    # might miss (the current-month calendar block).
    for meta in tree.css('.em-event-date'):
        text = meta.text(separator=" ")
        m = _RE_DATE_RANGE.search(text)
        if m:
            try:
                start = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                end = date(int(m.group(6)), int(m.group(4)), int(m.group(5)))
                pairs.add((start, end))
            except ValueError:
                pass

    return sorted(pairs)


def _format_date_range(start: date, end: date) -> str:
    if start == end:
        return f"{_MONTH_ABBR[start.month]} {start.day}, {start.year}"
    if start.month == end.month and start.year == end.year:
        return f"{_MONTH_ABBR[start.month]} {start.day}-{end.day}, {start.year}"
    if start.year == end.year:
        return (f"{_MONTH_ABBR[start.month]} {start.day} - "
                f"{_MONTH_ABBR[end.month]} {end.day}, {start.year}")
    return (f"{_MONTH_ABBR[start.month]} {start.day}, {start.year} - "
            f"{_MONTH_ABBR[end.month]} {end.day}, {end.year}")


# ---------- Course discovery ----------

def _discover_course_urls(tree: HTMLParser) -> list[str]:
    """Parse the 'Courses' nav dropdown to find course page URLs.

    Course entries are <a> links under menu items of type post_type/page
    that point to vetdentalclasses.com/<slug>/ (not the home page, not
    external). We dedupe and skip obvious non-course pages.
    """
    urls: list[str] = []
    seen: set[str] = set()
    skip_slugs = {
        "", "all-courses", "about", "about-us", "contact", "contact-us",
        "cart", "checkout", "my-account", "faq", "faqs", "blog",
        "privacy-policy", "terms", "terms-of-service",
    }
    for a in tree.css('li.menu-item-object-page a[href]'):
        href = (a.attributes.get("href") or "").strip()
        if not href.startswith(VDC_BASE):
            continue
        # Normalize: path between domain and trailing slash.
        path = href[len(VDC_BASE):].strip("/")
        if "/" in path:  # nested path, not a top-level course page
            continue
        if path in skip_slugs:
            continue
        if href in seen:
            continue
        # Heuristic: course pages have dentistry-ish slugs.
        if not re.search(
            r"dentist|extraction|periodontal|feline|oral-surgery|radiolog|wisdom|wet-lab",
            path, re.IGNORECASE,
        ):
            continue
        seen.add(href)
        urls.append(href)
    return urls


# ---------- The scraper ----------

class VetDentalClassesScraper(BaseScraper):
    SOURCE_SLUG = "vetdentalclasses"
    PROVIDER_NAME = "Animal Dental Care & Oral Surgery"
    LISTINGS_URL = f"{VDC_BASE}/all-courses/"
    REQUEST_DELAY = 2.0  # generous -- this site has rate-limited bots before

    def make_client(self) -> httpx.Client:
        """Present as a normal browser (this site blocks bare bot UAs)."""
        return httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        tree = HTMLParser(listings_html)
        course_urls = _discover_course_urls(tree)
        log.info("vetdentalclasses_courses_discovered", count=len(course_urls),
                 urls=course_urls)

        today = date.today()

        for i, url in enumerate(course_urls, start=1):
            try:
                page = self.fetch(url, client)
            except httpx.HTTPError as e:
                log.warning("vetdentalclasses_fetch_failed", url=url, error=str(e))
                continue

            ptree = HTMLParser(page)
            page_text = ptree.text(separator=" ")

            h1 = ptree.css_first("h1")
            title = _clean(h1.text()) if h1 is not None else None
            if not title:
                log.warning("vetdentalclasses_no_title", url=url)
                continue

            credit_hours, race_approved = _parse_credit_hours(page_text)
            cost = _parse_price(page_text)
            base_description = _parse_description(ptree)
            audience = _parse_audience(page_text)
            all_dates = _parse_all_dates(ptree)

            # Upcoming dates only (>= today), for starts_at + description.
            upcoming = [(s, e) for (s, e) in all_dates if e >= today]
            starts_at = upcoming[0][0] if upcoming else None
            ends_at = upcoming[0][1] if upcoming else None

            # Build description: original blurb + the full upcoming-date list.
            desc_parts: list[str] = []
            if base_description:
                desc_parts.append(base_description)
            if upcoming:
                date_strs = [_format_date_range(s, e) for (s, e) in upcoming]
                desc_parts.append("Upcoming dates: " + "; ".join(date_strs) + ".")
            if cost:
                desc_parts.append(f"Individual price: {cost}.")
            description = " ".join(desc_parts) or None

            log.info(
                "vetdentalclasses_course_parsed",
                n=i,
                title=title,
                credit_hours=str(credit_hours) if credit_hours else None,
                cost=cost,
                audience=audience,
                upcoming_dates=len(upcoming),
                next_date=str(starts_at) if starts_at else None,
            )

            yield RawListing(
                source_slug=self.SOURCE_SLUG,
                source_url=url,
                title=title,
                provider=self.PROVIDER_NAME,
                description=description,
                starts_at=starts_at,
                ends_at=ends_at,
                format="live",  # in-person lecture + wet lab
                cost=cost,
                race_approved=race_approved,
                credit_hours=credit_hours,
                audience=audience,
                registration_url=url,
                presenter="Dr. Patrick Vall, DAVDC",
            )


if __name__ == "__main__":
    VetDentalClassesScraper().run()