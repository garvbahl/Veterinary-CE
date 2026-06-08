"""Scraper for VetVine Videos on Demand (vetvine.com/videos-on-demand).

Structure:
- Paginated listings at /videos-on-demand?page=N (N=1..12 currently).
- Each listing card has: title, original presentation date, presenter(s),
  sponsor(s), truncated description, and a "Read More" link to the detail page.
- All data we need lives on the listings page itself — we do NOT fetch
  detail pages. Saves us ~120 detail-page requests per run.

Fields populated:
  title, source_url (the detail page URL), description (truncated),
  starts_at (original presentation date), format=on_demand,
  presenter, registration_url (the detail page).

Fields left NULL (not exposed publicly on VetVine):
  credit_hours, race_approved, audience, ends_at, cost.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


class VetVineScraper(BaseScraper):
    SOURCE_SLUG = "vetvine_videos_on_demand"
    LISTINGS_URL = "https://www.vetvine.com/videos-on-demand"
    PROVIDER_NAME = "VetVine"

    # Safety cap. The site currently has 12 pages; we'll iterate up to this
    # and stop early when a page returns no cards.
    MAX_PAGES = 30

    def list_pages(self) -> Iterable[str]:
        """Yield one URL per page. The base class fetches each via self.fetch()."""
        for page in range(1, self.MAX_PAGES + 1):
            yield f"{self.LISTINGS_URL}?page={page}"

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        """Parse one page of VetVine listings.

        client is unused — all data is on the listings page; no detail-page fetches.
        """
        tree = HTMLParser(listings_html)
        cards = tree.css("div.video-box-main")

        if not cards:
            # Likely paged past the end. Caller (list_pages loop) will continue
            # to next page; if all subsequent pages also empty, the run just
            # produces 0 listings for them. Cheap.
            log.info("vetvine_empty_page")
            return

        log.info("vetvine_cards_on_page", count=len(cards))

        for n, card in enumerate(cards, start=1):
            listing = _parse_card(card)
            if listing is None:
                continue
            log.info(
                "vetvine_card_parsed",
                n=n,
                title=listing.title[:60],
                starts_at=str(listing.starts_at),
                presenter=(listing.presenter or "")[:40],
            )
            yield listing


# ---------- Pure helpers (no class state) ----------

def _parse_card(card: Node) -> RawListing | None:
    """Map one .video-box-main card to a RawListing. Returns None to skip."""
    # Title
    title_node = card.css_first("div.video-bottom-text h3")
    if title_node is None:
        log.warning("vetvine_card_missing_title")
        return None
    title = title_node.text(strip=True)
    if not title:
        return None

    # Detail page URL — also our source_url (unique per listing) and registration_url
    read_more = card.css_first("a.read_more_btn")
    if read_more is None or not read_more.attributes.get("href"):
        log.warning("vetvine_card_missing_url", title=title[:60])
        return None
    source_url = read_more.attributes["href"]

    # Description (truncated on listings page; that's fine)
    desc_node = card.css_first("p.para-decription")
    description = desc_node.text(strip=True) if desc_node else None

    # Original presentation date — formatted as MM/DD/YYYY in an <h5>
    date_node = card.css_first("div.video-bottom-description h5")
    starts_at = _parse_date(date_node.text(strip=True)) if date_node else None

    # Presenter(s) — under "Presented by:" parent_sponser block
    presenter = _extract_role_value(card, "Presented by:")

    # Sponsor(s) — captured in description appendix for honesty
    sponsor = _extract_role_value(card, "Sponsored by:")
    if sponsor and description:
        description = f"{description}\n\nSponsored by: {sponsor}"
    elif sponsor:
        description = f"Sponsored by: {sponsor}"

    return RawListing(
        source_slug=VetVineScraper.SOURCE_SLUG,
        source_url=source_url,
        title=title,
        provider=VetVineScraper.PROVIDER_NAME,
        description=description,
        starts_at=starts_at,
        ends_at=None,
        format="on_demand",
        cost=None,           # Fee shown only on detail pages; we skip those.
        race_approved=None,  # Not publicly stated on listings page.
        race_program_number=None,
        credit_hours=None,   # Behind registration wall.
        presenter=presenter,
        audience=None,       # Not explicitly stated.
        delivery_method=None,
        subject_category=None,
        topics=None,
        registration_url=source_url,
    )


def _extract_role_value(card: Node, label: str) -> str | None:
    """Find a .parent_sponser block whose <strong> matches `label` and
    return the joined text of its child <a> tags (multiple presenters/sponsors
    are joined with ', '). Returns None if not found or empty.
    """
    for block in card.css("div.parent_sponser"):
        strong = block.css_first("strong")
        if strong is None:
            continue
        if strong.text(strip=True) != label:
            continue
        # Found the right block. Collect anchor texts.
        names = [
            a.text(strip=True)
            for a in block.css("a")
            if a.text(strip=True)
        ]
        return ", ".join(names) if names else None
    return None


def _parse_date(text: str) -> date | None:
    """Parse VetVine's MM/DD/YYYY date format into a `date`.

    Returns None on any unparseable input (with a warning).
    """
    if not text:
        return None
    text = text.strip()
    parts = text.split("/")
    if len(parts) != 3:
        log.warning("vetvine_date_unparseable", text=text)
        return None
    try:
        month, day, year = (int(p) for p in parts)
        return date(year, month, day)
    except (ValueError, TypeError) as e:
        log.warning("vetvine_date_parse_failed", text=text, error=str(e))
        return None


if __name__ == "__main__":
    from vetce.logging import configure_logging
    configure_logging()
    VetVineScraper().run()