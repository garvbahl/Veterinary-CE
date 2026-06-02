"""Scraper for NAVTA Continuing Education (ce.navta.net).

This site exposes its full course catalog as an embedded JSON
variable in the page source: `var courseData = '[...]'`.
We extract that variable, decode the JSON, and produce one
RawListing per course.

This is a fundamentally different extraction pattern from VetMedTeam:
no CSS selectors, no detail-page fetching. All data is on one page.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Iterable

import httpx

from vetce.config import settings
from vetce.logging import log
from vetce.pipeline.ingest import run_ingest
from vetce.scrapers.types import RawListing

SOURCE_SLUG = "navta_ce"
LISTINGS_URL = "https://ce.navta.net/"

# Match the embedded JS variable. The data is in single quotes after
# `var courseData = `. Single quotes inside the JSON are escaped as \'.
# We use DOTALL so `.` matches newlines inside the captured string.
_COURSE_DATA_RE = re.compile(
    r"var\s+courseData\s*=\s*'(?P<json>.*?)';",
    re.DOTALL,
)


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.user_agent},
        timeout=20.0,
        follow_redirects=True,
    )


def _extract_course_data(html: str) -> list[dict]:
    """Pull the courseData JSON out of the page source."""
    match = _COURSE_DATA_RE.search(html)
    if not match:
        raise ValueError("Could not find `var courseData` in the page source. "
                         "The page structure may have changed.")

    raw_json = match.group("json")

    # The JSON is embedded inside a JS single-quoted string, so single
    # quotes are escaped as \'. JSON itself doesn't recognize \' so we
    # unescape it manually before parsing.
    unescaped = raw_json.replace(r"\'", "'")

    try:
        return json.loads(unescaped)
    except json.JSONDecodeError as e:
        log.error("navta_json_decode_failed", error=str(e),
                  snippet=unescaped[:200])
        raise


def _parse_description_blob(blob: str) -> dict:
    """The `description` field on each course is itself a JSON string.

    The blob arrives with backslash-escaped quotes (e.g. \\" instead of ")
    because it was embedded inside an outer JSON string. We undo that
    escaping before parsing.

    Returns the parsed dict, or {} on failure (with a warning logged).
    """
    if not blob:
        return {}
    # Unescape backslash-escaped quotes from the outer JSON layer.
    unescaped = blob.replace('\\"', '"').replace("\\\\", "\\")
    try:
        return json.loads(unescaped)
    except json.JSONDecodeError as e:
        log.warning("navta_description_parse_failed", error=str(e),
                    snippet=unescaped[:120])
        return {}


def _to_credit_hours(value) -> float | None:
    """Course credits arrive as strings like '0.5', '1.0'. Convert safely."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _course_to_raw_listing(course: dict) -> RawListing | None:
    """Map one NAVTA course dict to a RawListing.

    NAVTA's data shape:
      - id_course: int — unique numeric ID
      - title: short internal name (e.g. "NAVTA CE OA Module 1")
      - description: JSON string with nested fields (title, subtitle,
        blurb, credits, sponsor, ceavailability, ...)
      - thumbnail: URL (we ignore for now)
    """
    course_id = course.get("id_course")
    if not course_id:
        log.warning("navta_course_missing_id", course=course)
        return None

    desc = _parse_description_blob(course.get("description", ""))

    # Prefer the human-readable title from the description blob;
    # fall back to the internal title.
    title = desc.get("title") or course.get("title") or ""
    subtitle = desc.get("subtitle") or ""
    if subtitle:
        title = f"{title} — {subtitle}" if title else subtitle

    blurb = desc.get("blurb") or None
    credits = _to_credit_hours(desc.get("credits"))
    sponsor = (desc.get("sponsor") or "").strip().lower() or None
    ce_availability = desc.get("ceavailability") or ""

    # Detect audience from "ceavailability" string.
    audience = None
    lowered = ce_availability.lower()
    if "veterinary technicians" in lowered and "veterinarians" in lowered:
        audience = "vets and techs"
    elif "veterinary technicians" in lowered or "nurses" in lowered:
        audience = "techs"
    elif "veterinarians" in lowered:
        audience = "vets"

    # Synthetic URL — NAVTA's actual detail pages are login-walled,
    # so we use the homepage with a fragment as the canonical reference.
    # source_url MUST be unique per listing (it's our identity key),
    # so we include the course id in the fragment.
    source_url = f"https://ce.navta.net/#course-{course_id}"

    # Description: if we have a blurb, prefix with sponsor/availability info.
    description_parts = []
    if blurb:
        description_parts.append(blurb)
    if ce_availability:
        description_parts.append(ce_availability)
    if sponsor:
        description_parts.append(f"Sponsored by {sponsor.title()}.")
    description = "\n\n".join(description_parts) if description_parts else None

    return RawListing(
        source_slug=SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider="NAVTA",
        description=description,
        format="on_demand",        # all NAVTA modules are self-paced
        cost="Free",               # all are free (CE credit at no cost)
        race_approved=None,        # not directly stated in JSON; leave honest
        credit_hours=credits,
        audience=audience,
        registration_url="https://ce.navta.net/",
    )


def scrape() -> Iterable[RawListing]:
    """Main entry point. Yields one RawListing per NAVTA course."""
    with _client() as client:
        log.info("fetch", url=LISTINGS_URL)
        resp = client.get(LISTINGS_URL)
        resp.raise_for_status()
        html = resp.text

    courses = _extract_course_data(html)
    log.info("navta_courses_found", count=len(courses))

    for i, course in enumerate(courses, start=1):
        listing = _course_to_raw_listing(course)
        if listing is None:
            continue
        log.info("navta_course_parsed", n=i, id=course.get("id_course"),
                 title=listing.title, credits=listing.credit_hours)
        yield listing


if __name__ == "__main__":
    from vetce.logging import configure_logging
    configure_logging()
    counts = run_ingest(scrape, source_slug=SOURCE_SLUG)
    print(f"\nDone: {counts}")