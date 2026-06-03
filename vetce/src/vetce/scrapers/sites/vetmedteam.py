"""Scraper for vetmedteam.com free courses.

Listings page:  https://www.vetmedteam.com/classes-free.aspx
Detail pages:   https://www.vetmedteam.com/class.aspx?ci=<id>

The listings page is a classic ASP.NET WebForms page (.aspx).
All courses sit in a single <table id="free-course-promotions">,
one course per <tr>. Each course's content cell has a stable class
of "free-course-promotion-content".

The detail page contains repeating <div class="course-detail-section">
blocks for RACE info, presenter, objectives, etc. We parse the whole
section text and pull fields out by regex.
"""
from __future__ import annotations

import re
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


# ---- Module-level parsers (kept as functions, not methods) ----

def _parse_listing_cells(html: str) -> list[tuple[str, str | None, str]]:
    """Return [(title, short_description, detail_url), ...] from the index page."""
    tree = HTMLParser(html)
    out: list[tuple[str, str | None, str]] = []

    cells = tree.css("td.free-course-promotion-content")
    log.info("listing_cells_found", count=len(cells))

    for cell in cells:
        title_node = cell.css_first("span.free-course-promotion-content-title")
        link_node = cell.css_first("a.free-course-promotion-content-link")

        if not title_node or not link_node:
            log.warning("listing_cell_missing_fields",
                        has_title=bool(title_node), has_link=bool(link_node))
            continue

        title = title_node.text(strip=True)
        href = link_node.attributes.get("href", "").strip()
        if not href:
            log.warning("listing_cell_no_href", title=title)
            continue

        description: str | None = None
        for span in cell.css("span"):
            classes = span.attributes.get("class", "") or ""
            if "free-course-promotion-content-title" in classes:
                continue
            text = span.text(strip=True)
            if text:
                description = text
                break

        out.append((title, description, href))

    return out


_RE_RACE_HOURS = re.compile(r"(\d+(?:\.\d+)?)\s*RACE\s*hours?", re.IGNORECASE)
_RE_PROGRAM_NUMBER = re.compile(r"Program\s*Number\s*([0-9A-Za-z\-]+)", re.IGNORECASE)
_RE_SUBJECT = re.compile(r"RACE\s*Subject\s*Category\s*:\s*([^;]+)", re.IGNORECASE)
_RE_DELIVERY = re.compile(r"Delivery\s*Method\s*:\s*([^;]+?)(?:;|$)", re.IGNORECASE)


def _parse_detail(url: str, html: str,
                  fallback_title: str,
                  fallback_description: str | None) -> RawListing:
    """Parse one detail page into a RawListing."""
    tree = HTMLParser(html)

    sections = tree.css("div.course-detail-section")
    combined_text = "\n\n".join(s.text(separator=" ", strip=True) for s in sections)

    race_approved: bool | None = None
    credit_hours: float | None = None
    race_program_number: str | None = None
    subject_category: str | None = None
    delivery_method: str | None = None
    audience: str | None = None

    if "RACE Approved" in combined_text or _RE_RACE_HOURS.search(combined_text):
        race_approved = True

    m = _RE_RACE_HOURS.search(combined_text)
    if m:
        try:
            credit_hours = float(m.group(1))
        except ValueError:
            log.warning("credit_hours_parse_failed", url=url, raw=m.group(0))

    m = _RE_PROGRAM_NUMBER.search(combined_text)
    if m:
        race_program_number = m.group(1)

    m = _RE_SUBJECT.search(combined_text)
    if m:
        subject_category = m.group(1).strip()

    m = _RE_DELIVERY.search(combined_text)
    if m:
        delivery_method = m.group(1).strip()

    lowered = combined_text.lower()
    if "vets and techs" in lowered or "veterinarians and veterinary technicians" in lowered:
        audience = "vets and techs"
    elif "veterinarians" in lowered:
        audience = "vets"
    elif "technicians" in lowered or "techs" in lowered:
        audience = "techs"

    presenter: str | None = None
    for sec in sections:
        text = sec.text(separator=" ", strip=True)
        if text.lower().startswith("content presenter"):
            presenter = text.replace("Content Presenter", "", 1).strip()
            break

    description: str | None = fallback_description
    for sec in sections:
        text = sec.text(separator=" ", strip=True)
        if "Course Focus and Learning Objectives" in text:
            description = text.split("Course Focus and Learning Objectives", 1)[1].strip()
            break

    title: str = fallback_title
    h1 = tree.css_first("h1")
    if h1:
        candidate = h1.text(strip=True)
        if candidate:
            title = candidate

    fmt = "on_demand" if "self-study" in lowered else None

    return RawListing(
        source_slug=VetMedTeamScraper.SOURCE_SLUG,
        source_url=url,
        title=title,
        provider=VetMedTeamScraper.PROVIDER_NAME,
        description=description,
        format=fmt,
        cost="Free",
        race_approved=race_approved,
        race_program_number=race_program_number,
        credit_hours=credit_hours,
        presenter=presenter,
        audience=audience,
        delivery_method=delivery_method,
        subject_category=subject_category,
        registration_url=url,
    )


# ---- The scraper class itself ----

class VetMedTeamScraper(BaseScraper):
    SOURCE_SLUG = "vetmedteam_free"
    PROVIDER_NAME = "VetMedTeam"
    LISTINGS_URL = "https://www.vetmedteam.com/classes-free.aspx"
    REQUEST_DELAY = 1.5  # be polite — per-request delay across detail pages

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        items = _parse_listing_cells(listings_html)
        log.info("listings_parsed", count=len(items))

        for i, (title, short_desc, detail_url) in enumerate(items, start=1):
            try:
                detail_html = self.fetch(detail_url, client)
                listing = _parse_detail(detail_url, detail_html,
                                        fallback_title=title,
                                        fallback_description=short_desc)
                log.info("course_parsed", n=i, title=listing.title,
                         credits=listing.credit_hours)
                yield listing
            except httpx.HTTPError as e:
                log.warning("detail_fetch_failed", url=detail_url, error=str(e))


if __name__ == "__main__":
    VetMedTeamScraper().run()