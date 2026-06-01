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
import time
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser

from vetce.config import settings
from vetce.logging import log
from vetce.scrapers.types import RawListing

SOURCE_SLUG = "vetmedteam"
LISTINGS_URL = "https://www.vetmedteam.com/classes-free.aspx"
REQUEST_DELAY_SECONDS = 1.5  # be polite — one request per ~1.5s


def _client() -> httpx.Client:
    """Build an HTTP client with our identifying User-Agent and a sane timeout."""
    return httpx.Client(
        headers={"User-Agent": settings.user_agent},
        timeout=20.0,
        follow_redirects=True,
    )


def _fetch(url: str, client: httpx.Client) -> str:
    log.info("fetch", url=url)
    resp = client.get(url)
    resp.raise_for_status()
    return resp.text


def parse_listings(html: str) -> list[tuple[str, str | None, str]]:
    """Return [(title, short_description, detail_url), ...] from the listings page."""
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

        # description is the *other* span in the cell (the one without the title class)
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


# regex patterns for the detail page
_RE_RACE_HOURS = re.compile(r"(\d+(?:\.\d+)?)\s*RACE\s*hours?", re.IGNORECASE)
_RE_PROGRAM_NUMBER = re.compile(r"Program\s*Number\s*([0-9A-Za-z\-]+)", re.IGNORECASE)
_RE_SUBJECT = re.compile(r"RACE\s*Subject\s*Category\s*:\s*([^;]+)", re.IGNORECASE)
_RE_DELIVERY = re.compile(r"Delivery\s*Method\s*:\s*([^;]+?)(?:;|$)", re.IGNORECASE)


def parse_detail(url: str, html: str,
                 fallback_title: str, fallback_description: str | None) -> RawListing:
    """Parse one detail page into a RawListing.

    The page is structured as repeating <div class="course-detail-section"> blocks.
    We don't know which section contains which info, so we concatenate the
    text of all sections and pull fields by regex.
    """
    tree = HTMLParser(html)

    sections = tree.css("div.course-detail-section")
    combined_text = "\n\n".join(s.text(separator=" ", strip=True) for s in sections)

    # ---- RACE info ----
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

    # crude audience detection from a likely section header
    lowered = combined_text.lower()
    if "vets and techs" in lowered or "veterinarians and veterinary technicians" in lowered:
        audience = "vets and techs"
    elif "veterinarians" in lowered:
        audience = "vets"
    elif "technicians" in lowered or "techs" in lowered:
        audience = "techs"

    # ---- Presenter ----
    presenter: str | None = None
    # find the section whose header is "Content Presenter"
    for sec in sections:
        text = sec.text(separator=" ", strip=True)
        if text.lower().startswith("content presenter"):
            # text looks like "Content Presenter Lauren Forsythe, PharmD, ..."
            presenter = text.replace("Content Presenter", "", 1).strip()
            break

    # ---- Description ----
    description: str | None = fallback_description
    for sec in sections:
        text = sec.text(separator=" ", strip=True)
        if "Course Focus and Learning Objectives" in text:
            # strip the header out, keep the rest
            description = text.split("Course Focus and Learning Objectives", 1)[1].strip()
            break

    # ---- Title ----
    # try page <h1> or <title> if available; else use the title from the listings page
    title: str = fallback_title
    h1 = tree.css_first("h1")
    if h1:
        candidate = h1.text(strip=True)
        if candidate:
            title = candidate

    # all VetMedTeam free courses are on-demand self-study; webinars are separate
    fmt = "on_demand" if "self-study" in lowered else None

    return RawListing(
        source_slug=SOURCE_SLUG,
        source_url=url,
        title=title,
        provider="VetMedTeam",
        description=description,
        format=fmt,
        cost="Free",  # listings page is /classes-free.aspx — guaranteed free
        race_approved=race_approved,
        race_program_number=race_program_number,
        credit_hours=credit_hours,
        presenter=presenter,
        audience=audience,
        delivery_method=delivery_method,
        subject_category=subject_category,
        registration_url=url,
    )


def scrape() -> Iterable[RawListing]:
    """Main entry point. Yields RawListing objects, one per course."""
    with _client() as client:
        listings_html = _fetch(LISTINGS_URL, client)
        items = parse_listings(listings_html)
        log.info("listings_parsed", count=len(items))

        for i, (title, short_desc, detail_url) in enumerate(items, start=1):
            try:
                time.sleep(REQUEST_DELAY_SECONDS)  # be a polite citizen
                detail_html = _fetch(detail_url, client)
                listing = parse_detail(detail_url, detail_html,
                                       fallback_title=title,
                                       fallback_description=short_desc)
                log.info("course_parsed", n=i, title=listing.title,
                         credits=listing.credit_hours)
                yield listing
            except httpx.HTTPError as e:
                log.warning("detail_fetch_failed", url=detail_url, error=str(e))


if __name__ == "__main__":
    from vetce.logging import configure_logging
    from vetce.pipeline.ingest import run_ingest

    configure_logging()
    counts = run_ingest(scrape, source_slug="vetmedteam_free")
    print(f"\nDone: {counts}")