"""Scraper for Periovive's Thinkific on-demand course catalog.

Source page: periovive.thinkific.com/collections

Structure:
- Thinkific's standard Liquid theme. Course cards on the collections page:
    <li class="products__list-item">
      <a class="card card--published card--course" href="/products/courses/<slug>">
        <img class="card__img" src="..." />
        <h3 class="card__name">Title</h3>
        <span class="card__product-info"><i.../> Course </span>
        <p class="card__description">Short description</p>
        <span class="card__badge card__badge--free">Free</span>  -- or --
        <p class="card__price">$XX</p>
      </a>
    </li>
- We follow each course link to extract presenter and RACE credit hours
  from the detail page. Those live in titled <h2 class="title"> blocks:
    "Earn one hour of RACE-Approved CE"
    "Meet Your Instructor: Dr. Jan Bellows"

This is a fifth extraction pattern: listings HTML + per-item detail fetch.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


THINKIFIC_BASE = "https://periovive.thinkific.com"


# ---------- Credit hours parsing ----------

_NUMBER_WORDS = {
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "half": 0.5,
}

# Matches "Earn one hour", "Earn 2 hours", "Earn 1.5 hours of RACE..."
_RE_EARN_CREDITS = re.compile(
    r"Earn\s+(?P<amount>[a-zA-Z]+|\d+(?:\.\d+)?)\s+hours?\s+of\s+RACE",
    re.IGNORECASE,
)


def _parse_credit_hours(heading_text: str) -> Decimal | None:
    """Parse 'Earn one hour of RACE-Approved CE' -> Decimal(1.0)."""
    if not heading_text:
        return None
    m = _RE_EARN_CREDITS.search(heading_text)
    if not m:
        return None
    amount = m.group("amount").lower()
    if amount in _NUMBER_WORDS:
        return Decimal(str(_NUMBER_WORDS[amount]))
    try:
        return Decimal(amount)
    except (ValueError, ArithmeticError):
        return None


# ---------- Presenter parsing ----------

# "Meet Your Instructor: Dr. Jan Bellows" -> "Dr. Jan Bellows"
_RE_INSTRUCTOR = re.compile(
    r"Meet\s+Your\s+Instructor:\s*(?P<name>.+)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_presenter(heading_text: str) -> str | None:
    if not heading_text:
        return None
    m = _RE_INSTRUCTOR.search(heading_text)
    if not m:
        return None
    name = m.group("name").strip()
    # Collapse internal whitespace (the heading splits across newlines).
    name = re.sub(r"\s+", " ", name)
    return name or None


# ---------- Listings page extraction ----------

def _extract_course_cards(html: str) -> list[dict]:
    """Return one dict per course card on the collections listings page.

    Filters to course-type products only (skips bundles, communities, etc).
    """
    tree = HTMLParser(html)
    cards: list[dict] = []

    for anchor in tree.css("a.card.card--course"):
        href = anchor.attributes.get("href")
        if not href:
            continue
        # Skip any anchor that isn't a course product (defensive — class filter
        # above should already handle this).
        if "/products/courses/" not in href:
            continue

        title_node = anchor.css_first("h3.card__name")
        desc_node = anchor.css_first("p.card__description")
        free_badge = anchor.css_first("span.card__badge--free")
        price_node = anchor.css_first("p.card__price")
        img_node = anchor.css_first("img.card__img")

        title = title_node.text(strip=True) if title_node else None
        if not title:
            continue

        # Cost: "Free" if badge present, else strip the price text.
        if free_badge is not None:
            cost = "Free"
        elif price_node is not None:
            cost = price_node.text(strip=True) or None
        else:
            cost = None

        cards.append({
            "title": title,
            "description": desc_node.text(strip=True) if desc_node else None,
            "href": href if href.startswith("http") else THINKIFIC_BASE + href,
            "image_url": img_node.attributes.get("src") if img_node else None,
            "cost": cost,
        })

    return cards


# ---------- Detail page extraction ----------

def _extract_detail_fields(detail_html: str) -> dict:
    """Pull presenter + credit_hours + race_approved from a course detail page."""
    tree = HTMLParser(detail_html)

    credit_hours: Decimal | None = None
    presenter: str | None = None
    race_approved: bool | None = None

    # Walk every <h2 class="title"> on the page; assign by content match.
    for h2 in tree.css("h2.title"):
        text = h2.text(separator=" ", strip=True)
        if not text:
            continue
        if "RACE" in text.upper() and credit_hours is None:
            credit_hours = _parse_credit_hours(text)
            if credit_hours is not None:
                race_approved = True
        if "Meet Your Instructor" in text and presenter is None:
            presenter = _parse_presenter(text)

    return {
        "credit_hours": credit_hours,
        "presenter": presenter,
        "race_approved": race_approved,
    }


# ---------- Mapping to RawListing ----------

def _card_to_raw_listing(
    card: dict, detail_fields: dict
) -> RawListing | None:
    title = (card.get("title") or "").strip()
    if not title:
        return None

    description = card.get("description")
    # Pad description with image-url-derived context if helpful? No — honest
    # over impressive. Leave None if Thinkific didn't supply one.

    return RawListing(
        source_slug=PerioviveThinkificScraper.SOURCE_SLUG,
        source_url=card["href"],
        title=title,
        provider=PerioviveThinkificScraper.PROVIDER_NAME,
        description=description,
        starts_at=None,  # on-demand, no schedule
        ends_at=None,
        format="on_demand",
        cost=card.get("cost"),
        race_approved=detail_fields.get("race_approved"),
        credit_hours=detail_fields.get("credit_hours"),
        audience=None,  # not consistently stated on detail pages
        registration_url=card["href"],  # the enrollment is the course page itself
        presenter=detail_fields.get("presenter"),
    )


# ---- The scraper class itself ----

class PerioviveThinkificScraper(BaseScraper):
    SOURCE_SLUG = "periovive_thinkific"
    PROVIDER_NAME = "Periovive"
    LISTINGS_URL = f"{THINKIFIC_BASE}/collections"
    REQUEST_DELAY = 0.5  # be polite — 10 detail fetches per run
    
    MAX_PAGES = 20  # safety ceiling; loop stops earlier when a page is empty

    def list_pages(self) -> Iterable[str]:
        for page in range(1, self.MAX_PAGES + 1):
            yield f"{self.LISTINGS_URL}?page={page}"

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        cards = _extract_course_cards(listings_html)
        log.info("periovive_thinkific_cards_found", count=len(cards))

        for i, card in enumerate(cards, start=1):
            try:
                detail_html = self.fetch(card["href"], client)
                detail_fields = _extract_detail_fields(detail_html)
            except httpx.HTTPError as e:
                log.warning(
                    "periovive_thinkific_detail_fetch_failed",
                    n=i,
                    title=card["title"],
                    href=card["href"],
                    error=str(e),
                )
                detail_fields = {
                    "credit_hours": None,
                    "presenter": None,
                    "race_approved": None,
                }

            listing = _card_to_raw_listing(card, detail_fields)
            if listing is None:
                log.info(
                    "periovive_thinkific_skipped_empty_title",
                    n=i,
                    href=card.get("href"),
                )
                continue

            log.info(
                "periovive_thinkific_course_parsed",
                n=i,
                title=listing.title,
                cost=listing.cost,
                credit_hours=str(listing.credit_hours) if listing.credit_hours else None,
                race=listing.race_approved,
                presenter=listing.presenter,
            )
            yield listing


if __name__ == "__main__":
    PerioviveThinkificScraper().run()