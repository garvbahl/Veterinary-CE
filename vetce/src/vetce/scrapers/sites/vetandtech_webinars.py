"""Scraper for Vet and Tech webinars (vetandtech.com) -- dental only.

Vet and Tech is a first-party veterinary CE platform (it runs its own
RACE-approved webinars; it is NOT a directory). The site is a Next.js SPA,
so the rendered HTML is an empty shell -- BUT every detail page embeds the
full webinar record as JSON inside a <script id="__NEXT_DATA__"> tag.

Architecture:
- The sitemap index points to webinars-sitemap.xml, which lists all 83
  webinar detail URLs (authoritative, no pagination guesswork).
- For each URL: fetch the page, extract the __NEXT_DATA__ JSON, read
  props.pageProps.result.webinar, and keep only those whose `categories`
  string contains "Dentistry".
- source_url is the clean sitemap URL (no hash-fragment hacks needed).

Field mapping (webinar object -> RawListing):
- name              -> title
- slug              -> (used in source_url, already have full URL from sitemap)
- ce_hours          -> credit_hours
- race_approved (1) -> race_approved (bool)
- start_date        -> starts_at   (format "YYYY-MM-DD HH:MM:SS")
- end_date          -> ends_at
- full_detail/short_detail -> description (HTML stripped)
- speaker (object)  -> presenter ("First Last, Job Title")
- webinar_type + start_date -> format (past dated = on_demand, future = live)
- categories (str)  -> dental filter ("Dentistry, ...")

KNOWN FRAGILITY: if Vet and Tech changes their Next.js data shape (renames
result.webinar or the __NEXT_DATA__ structure), extraction returns zero and
logs a warning -- loud failure, not silent bad data.
"""
from __future__ import annotations

import html as html_module
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

import httpx
from selectolax.parser import HTMLParser

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


VT_BASE = "https://www.vetandtech.com"
SITEMAP_URL = f"{VT_BASE}/webinars-sitemap.xml"

# Matches the embedded Next.js data blob.
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


def _strip_html(raw: str | None) -> str | None:
    if not raw:
        return None
    text = HTMLParser(raw).text(separator=" ")
    text = html_module.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        # Fall back to a date-only prefix.
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def _parse_credit_hours(value: Any) -> Decimal | None:
    if value is None:
        return None
    s = str(value).strip()
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        v = Decimal(m.group(0))
        return v if v > 0 else None
    except (ValueError, ArithmeticError):
        return None


def _is_dental(categories_value: Any) -> bool:
    """webinar.categories is a comma-separated string like 'Dentistry, '."""
    if not categories_value:
        return False
    return "dentistry" in str(categories_value).lower()


def _speaker_name(speaker: Any) -> str | None:
    if not isinstance(speaker, dict):
        return None
    first = (speaker.get("first_name") or "").strip()
    last = (speaker.get("last_name") or "").strip()
    name = f"{first} {last}".strip()
    if not name:
        return None
    job = (speaker.get("job_title") or "").strip()
    return f"{name}, {job}" if job else name


def _parse_format(webinar: dict[str, Any], starts_at: Any) -> str:
    """A future-dated webinar is live; a past one is available on-demand
    (Vet and Tech keeps recordings up for CE -- allow_video/video_id present)."""
    if starts_at is None:
        return "on_demand"
    from datetime import date as _date
    if starts_at >= _date.today():
        return "live"
    # Past event -- on-demand if a recording exists, else still mark on_demand
    # (Vet and Tech keeps past webinars available to watch for CE).
    return "on_demand"


def _sitemap_urls(xml_text: str) -> list[str]:
    urls: list[str] = []
    for m in re.finditer(r"<loc>\s*(.*?)\s*</loc>", xml_text, re.DOTALL):
        url = m.group(1).strip()
        if "/webinars/" in url:
            urls.append(url)
    return urls


def _extract_webinar(html_text: str) -> dict[str, Any] | None:
    m = _NEXT_DATA_RE.search(html_text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    try:
        return data["props"]["pageProps"]["result"]["webinar"]
    except (KeyError, TypeError):
        return None


class VetAndTechWebinarsScraper(BaseScraper):
    SOURCE_SLUG = "vetandtech_webinars"
    PROVIDER_NAME = "Vet and Tech"
    LISTINGS_URL = SITEMAP_URL
    REQUEST_DELAY = 0.4  # polite pacing across ~83 detail fetches

    def list_pages(self) -> Iterable[str]:
        """Single entry point: the sitemap. extract_listings does the rest."""
        yield SITEMAP_URL

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        # listings_html is the webinars sitemap XML (base fetched it for us).
        urls = _sitemap_urls(listings_html)
        log.info("vetandtech_sitemap_urls", count=len(urls))

        total_dental = 0
        for i, url in enumerate(urls, start=1):
            try:
                page = self.fetch(url, client)
            except httpx.HTTPError as e:
                log.warning("vetandtech_fetch_failed", url=url, error=str(e))
                continue

            webinar = _extract_webinar(page)
            if webinar is None:
                log.warning("vetandtech_no_next_data", url=url)
                continue

            if not _is_dental(webinar.get("categories")):
                continue

            title = (webinar.get("name") or "").strip()
            if not title:
                continue

            starts_dt = _parse_dt(webinar.get("start_date"))
            ends_dt = _parse_dt(webinar.get("end_date"))
            starts_at = starts_dt.date() if starts_dt else None
            ends_at = ends_dt.date() if ends_dt else None
            description = _strip_html(
                webinar.get("full_detail") or webinar.get("short_detail")
            )
            credit_hours = _parse_credit_hours(webinar.get("ce_hours"))
            race_approved = str(webinar.get("race_approved", "")).strip() in ("1", "true", "True")
            presenter = _speaker_name(webinar.get("speaker"))
            fmt = _parse_format(webinar, starts_at)
            total_dental += 1
            log.info(
                "vetandtech_dental_webinar",
                n=i,
                title=title,
                ce=str(credit_hours) if credit_hours else None,
                starts_at=str(starts_at) if starts_at else None,
                fmt=fmt,
            )

            yield RawListing(
                source_slug=self.SOURCE_SLUG,
                source_url=url,
                title=title,
                provider=self.PROVIDER_NAME,
                description=description,
                starts_at=starts_at,
                ends_at=ends_at,
                format=fmt,
                cost="Free",  # Vet and Tech webinars are free
                race_approved=race_approved,
                credit_hours=credit_hours,
                audience="vets and techs",
                registration_url=url,
                presenter=presenter,
            )

        log.info("vetandtech_total_dental", count=total_dental)


if __name__ == "__main__":
    VetAndTechWebinarsScraper().run()