"""Reusable scraper for Canvas Catalog vet-school CE catalogs.

Canvas Catalog (Instructure's product, *.catalog.instructure.com) powers CE
catalogs at many veterinary schools. The browse page is a JS shell, but each
catalog exposes a PUBLIC JSON endpoint with no auth:

    https://{subdomain}.catalog.instructure.com/browse/{catalog_slug}.json

It returns {"products": [...]} with clean per-course fields. This base class
handles the fetch + field mapping; each school is a thin subclass that sets
SUBDOMAIN, CATALOG_SLUG, SOURCE_SLUG, and PROVIDER_NAME.

Field mapping (product -> RawListing):
- title       -> title
- credits     -> credit_hours  (measurement == "credit")
- price/free  -> cost          ("Free" if free, else "$N")
- url         -> source_url / registration_url
- teaser      -> description
- type/days   -> format        (self-paced online -> on_demand)

NOTE: startDate in the JSON is the course CREATION date (often years old) for
self-paced/on-demand courses, NOT a scheduled event date. We therefore set
starts_at = None for on-demand courses rather than using a misleading past date.

These are AVMA-approved CE providers (RACE-equivalent), so race_approved=True.
The catalog is all-discipline (not dental-only); the AI tagger filters to
dental downstream.
"""
from __future__ import annotations

import html as html_module
import json
import re
from decimal import Decimal
from typing import Iterable

import httpx

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    t = re.sub(r"<[^>]+>", " ", text)
    t = html_module.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _parse_credits(product: dict) -> Decimal | None:
    measurement = str(product.get("measurement") or "").lower()
    if "credit" not in measurement and "hour" not in measurement:
        # Unknown unit; still try the number but be cautious.
        pass
    raw = product.get("credits")
    if raw is None:
        return None
    try:
        v = Decimal(str(raw))
        return v if v > 0 else None
    except (ValueError, ArithmeticError):
        return None


def _parse_cost(product: dict) -> str | None:
    if product.get("free") in (True, "True", "true"):
        return "Free"
    price = product.get("price")
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except (ValueError, ArithmeticError):
        return None
    if p == 0:
        return "Free"
    cur = product.get("currency") or "USD"
    sym = "$" if cur == "USD" else ""
    if p == p.to_integral_value():
        return f"{sym}{int(p):,}"
    return f"{sym}{p:,.2f}"


def _parse_format(product: dict) -> str:
    # Canvas Catalog self-paced courses have daysToComplete and no real event
    # schedule -> on_demand. If a future-dated live offering ever appears we can
    # refine, but the catalog is overwhelmingly self-paced online CE.
    days = product.get("daysToComplete")
    if days:
        return "on_demand"
    t = str(product.get("type") or "").lower()
    if "lab" in t or "live" in t:
        return "hybrid"
    return "on_demand"


class CanvasCatalogScraper(BaseScraper):
    """Base class. Subclass and set the four class attributes below."""

    # --- subclasses MUST set these ---
    SUBDOMAIN: str = ""          # e.g. "tuftsce"
    CATALOG_SLUG: str = ""       # e.g. "ce-vet"
    SOURCE_SLUG: str = ""
    PROVIDER_NAME: str = ""
    # ---------------------------------

    REQUEST_DELAY = 0.5

    def _base_url(self) -> str:
        return f"https://{self.SUBDOMAIN}.catalog.instructure.com"

    def make_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            },
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def list_pages(self) -> Iterable[str]:
        yield f"{self._base_url()}/browse/{self.CATALOG_SLUG}.json"

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        try:
            data = json.loads(listings_html)
        except json.JSONDecodeError:
            log.warning("canvas_catalog_bad_json", source=self.SOURCE_SLUG)
            return

        products = data.get("products") or []
        log.info("canvas_catalog_products", source=self.SOURCE_SLUG,
                 count=len(products))

        for p in products:
            title = _clean(p.get("title"))
            if not title:
                continue

            url = p.get("url")
            if not url:
                path = p.get("path")
                if path:
                    url = f"{self._base_url()}/browse/{self.CATALOG_SLUG}/courses/{path}"

            credit_hours = _parse_credits(p)
            cost = _parse_cost(p)
            description = _clean(p.get("teaser"))
            fmt = _parse_format(p)

            log.info(
                "canvas_catalog_course",
                source=self.SOURCE_SLUG,
                title=title,
                credits=str(credit_hours) if credit_hours else None,
                cost=cost,
                fmt=fmt,
            )

            yield RawListing(
                source_slug=self.SOURCE_SLUG,
                source_url=url,
                title=title,
                provider=self.PROVIDER_NAME,
                description=description,
                starts_at=None,   # creation date is not an event date
                ends_at=None,
                format=fmt,
                cost=cost,
                race_approved=True,  # AVMA-approved CE provider (RACE-equivalent)
                credit_hours=credit_hours,
                audience="vets and techs",
                registration_url=url,
                presenter=None,  # named in teaser, not a structured field
            )


class TuftsVetCEScraper(CanvasCatalogScraper):
    SUBDOMAIN = "tuftsce"
    CATALOG_SLUG = "ce-vet"
    SOURCE_SLUG = "tufts_vet_ce"
    PROVIDER_NAME = "Tufts Cummings School of Veterinary Medicine"


if __name__ == "__main__":
    TuftsVetCEScraper().run()