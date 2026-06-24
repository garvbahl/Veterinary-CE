"""Scraper for VetFolio's catalog (vetfolio.com) — dental items only.

Source endpoint:
    https://www.vetfolio.com/learn/browse?page=N&layoutId=...&widgetId=...

VetFolio is a Thought Industries LMS (NAVC's platform). The front end is a
client-rendered SPA, but the catalog data comes from a clean, PUBLIC JSON
endpoint — no auth, no cookies, no nonce required. We hit it directly.

Structure:
- Each page returns {"contentItems": [...48 items...], "meta": {...}}.
- meta.total is the catalog-wide item count; meta.hasMore signals more pages.
- Each content item has:
    title, slug, description, contentTypeLabel, displayCourseSlug,
    courseStartDate (sometimes), and a customFields[] array of "key::value"
    strings: ces::1, cost::Free Access, topics::Dentistry, speaker::Name,
    content-type::Live Webinar, race-program-number::20-1383213,
    professional-roles::Veterinarian, etc.

VetFolio is a broad multi-topic catalog (1480 items across 38 topics). We
filter CLIENT-SIDE to items tagged topics::Dentistry, since the endpoint
ignores the labels/values filter params. The AI tagger is the backstop.

Item -> URL mapping:
- contentTypeLabel "CE Article" -> /learn/article/{displayCourseSlug}
- everything else (Course, Live Webinar, Microlearning, Subscription, ...) ->
  /courses/{displayCourseSlug or slug}

KNOWN FRAGILITY: layoutId / widgetId are baked into the catalog widget. If
VetFolio rebuilds their catalog page these IDs change and the scraper 404s
(loudly — we'll see zero results and a non-200, not silent bad data). Refresh
them by re-capturing the browse XHR in DevTools.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

import httpx

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


VETFOLIO_BASE = "https://www.vetfolio.com"
LAYOUT_ID = "898c6e11-ded8-417f-81bf-c38a86a41ee1"
WIDGET_ID = "xreuyc1"
BROWSE_PATH = "/learn/browse"
PAGE_SIZE = 48  # the endpoint's fixed page size
MAX_PAGES = 60  # safety ceiling (1480 items / 48 ≈ 31 pages; 60 is generous)

DENTAL_TOPIC = "topics::Dentistry"


# ---------- customFields helpers ----------

def _custom_fields_to_dict(fields: list[str]) -> dict[str, list[str]]:
    """Turn ['ces::1', 'topics::Dentistry', 'topics::Oral Surgery'] into
    {'ces': ['1'], 'topics': ['Dentistry', 'Oral Surgery']}.

    A key can appear multiple times (topics, species, professional-roles,
    content-type), so values are always lists.
    """
    out: dict[str, list[str]] = {}
    for raw in fields or []:
        if "::" not in raw:
            continue
        key, _, value = raw.partition("::")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        out.setdefault(key, []).append(value)
    return out


def _is_dental(fields: list[str]) -> bool:
    """True if the item is tagged with the Dentistry topic."""
    return any(f.strip() == DENTAL_TOPIC for f in (fields or []))


def _first(d: dict[str, list[str]], key: str) -> str | None:
    vals = d.get(key)
    return vals[0] if vals else None


# ---------- field parsing ----------

def _parse_credit_hours(ces_value: str | None) -> Decimal | None:
    """ces is usually a bare number ('1', '0.5', '24') but can be
    'Informational Only' or similar non-numeric labels."""
    if not ces_value:
        return None
    m = re.search(r"\d+(?:\.\d+)?", ces_value)
    if not m:
        return None
    try:
        v = Decimal(m.group(0))
        return v if v > 0 else None
    except (ValueError, ArithmeticError):
        return None


def _parse_cost(cost_values: list[str] | None) -> str | None:
    """cost can have multiple values ('Included with Subscription',
    'Free Access'). Prefer the most learner-friendly phrasing."""
    if not cost_values:
        return None
    joined = [c for c in cost_values if c]
    if not joined:
        return None
    # Prefer "Free Access" if present, else the first value.
    for c in joined:
        if "free" in c.lower():
            return c
    return joined[0]


def _parse_audience(roles: list[str] | None) -> str | None:
    if not roles:
        return None
    lowered = " ".join(roles).lower()
    has_vet = "veterinarian" in lowered
    has_tech = "technician" in lowered or "nurse" in lowered
    if has_vet and has_tech:
        return "vets and techs"
    if has_vet:
        return "vets"
    if has_tech:
        return "techs"
    return None


def _parse_format(content_type: str | None, start_date: date | None) -> str | None:
    """Map VetFolio content type to our format slug."""
    if not content_type:
        return "on_demand"
    lowered = content_type.lower()
    if "live webinar" in lowered or "live" in lowered:
        return "live"
    # Courses, articles, microlearnings, video libraries are self-paced.
    return "on_demand"


def _parse_start_date(item: dict[str, Any]) -> date | None:
    raw = item.get("courseStartDate") or item.get("publishDate")
    if not raw:
        return None
    try:
        # ISO 8601 with Z suffix, e.g. "2026-09-23T04:00:00.000Z"
        cleaned = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned).date()
    except (ValueError, TypeError):
        # Fall back to a plain date prefix match.
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def _build_url(item: dict[str, Any]) -> str:
    slug = item.get("displayCourseSlug") or item.get("slug") or ""
    content_label = (item.get("contentTypeLabel") or "").lower()
    if "article" in content_label:
        return f"{VETFOLIO_BASE}/learn/article/{slug}"
    return f"{VETFOLIO_BASE}/courses/{slug}"


# ---------- item -> RawListing ----------

def _item_to_listing(item: dict[str, Any]) -> RawListing | None:
    fields_raw = item.get("customFields") or []
    if not _is_dental(fields_raw):
        return None

    title = (item.get("title") or "").strip()
    if not title:
        return None

    # Skip subscription/bundle products — they're not individual CE listings.
    kind = (item.get("kind") or "").lower()
    if kind == "bundle":
        return None

    fields = _custom_fields_to_dict(fields_raw)

    description = (item.get("description") or "").strip() or None
    credit_hours = _parse_credit_hours(_first(fields, "ces"))
    cost = _parse_cost(fields.get("cost"))
    audience = _parse_audience(fields.get("professional-roles"))
    content_type = _first(fields, "content-type") or item.get("contentTypeLabel")
    starts_at = _parse_start_date(item)
    fmt = _parse_format(content_type, starts_at)
    presenter = _first(fields, "speaker")
    race_number = _first(fields, "race-program-number")
    race_approved = True if race_number else None

    source_url = _build_url(item)

    return RawListing(
        source_slug=VetfolioCatalogScraper.SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider=VetfolioCatalogScraper.PROVIDER_NAME,
        description=description,
        starts_at=starts_at,
        ends_at=None,
        format=fmt,
        cost=cost,
        race_approved=race_approved,
        credit_hours=credit_hours,
        audience=audience,
        registration_url=source_url,
        presenter=presenter,
    )


# ---------- The scraper class ----------

class VetfolioCatalogScraper(BaseScraper):
    SOURCE_SLUG = "vetfolio_catalog"
    PROVIDER_NAME = "VetFolio"
    LISTINGS_URL = (
        f"{VETFOLIO_BASE}{BROWSE_PATH}"
        f"?layoutId={LAYOUT_ID}&widgetId={WIDGET_ID}"
    )
    REQUEST_DELAY = 0.5  # polite pacing across ~31 pages

    def make_client(self) -> httpx.Client:
        """VetFolio's browse endpoint returns JSON only when the request
        is marked as XHR via the X-Requested-With header."""
        from vetce.config import settings
        return httpx.Client(
            headers={
                "User-Agent": settings.user_agent,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
            },
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    
    def list_pages(self) -> Iterable[str]:
        """We paginate internally in extract_listings, so the base class
        only needs to invoke us once. Yield page 1; the rest is handled
        by the loop in extract_listings."""
        yield f"{self.LISTINGS_URL}&page=1"    
    
    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        """Paginate the browse endpoint, filtering to dental items.

        listings_html here is the page-1 JSON text (the base class fetches
        LISTINGS_URL = page 1 implicitly). We parse it, then page through
        the rest using meta.hasMore.
        """
        total_dental = 0
        seen_urls: set[str] = set()

        for page in range(1, MAX_PAGES + 1):
            if page == 1:
                # The base class already fetched page 1 and handed it to us.
                raw = listings_html
            else:
                url = f"{self.LISTINGS_URL}&page={page}"
                try:
                    raw = self.fetch(url, client)
                except httpx.HTTPError as e:
                    log.warning("vetfolio_page_fetch_failed", page=page, error=str(e))
                    break

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                log.warning("vetfolio_invalid_json", page=page, error=str(e))
                break

            items = payload.get("contentItems") or []
            meta = payload.get("meta") or {}
            has_more = bool(meta.get("hasMore"))

            page_dental = 0
            for item in items:
                listing = _item_to_listing(item)
                if listing is None:
                    continue
                if listing.source_url in seen_urls:
                    continue
                seen_urls.add(listing.source_url)
                page_dental += 1
                total_dental += 1
                log.info(
                    "vetfolio_dental_item",
                    page=page,
                    title=listing.title,
                    ces=str(listing.credit_hours) if listing.credit_hours else None,
                    fmt=listing.format,
                )
                yield listing

            log.info(
                "vetfolio_page_done",
                page=page,
                items=len(items),
                dental=page_dental,
                has_more=has_more,
            )

            if not has_more or not items:
                break

        log.info("vetfolio_total_dental", count=total_dental)


if __name__ == "__main__":
    VetfolioCatalogScraper().run()