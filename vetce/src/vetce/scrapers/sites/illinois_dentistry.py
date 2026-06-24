"""Scraper for University of Illinois CVM dental CE courses.

Source page:
    vetmed.illinois.edu/ope2/online-vetmed/programs/continuing-education/

Structure:
- A single static page lists CE courses across multiple categories
  (Biosecurity, Infectious Disease, Dentistry, Assorted). Each category
  is opened by an <h2 class="wp-block-heading" id="..."> header.
- We scope strictly to the Dentistry section by finding the <h2 id="dentistry">
  and collecting <il-clickable-card> elements until the next <h2>.
- Each course card looks like:
    <il-clickable-card href="https://illinois.catalog.instructure.com/browse/veterinary-medicine/courses/24ce-clinical-small-animal-dentistry">
        <img ... slot="image">
        <h3 slot="header">Clinical Small Animal Dentistry (24 CE Hrs)</h3>
        <p>This course is an intensive study of modern dentistry techniques for dogs and cats.</p>
    </il-clickable-card>
- Each course has its own Canvas catalog URL on the parent `<il-clickable-card>`
  href attribute. We use that as the source_url and registration_url — no
  hash-fragment hack needed.
- All Illinois dental courses are self-paced, on-demand, "RACE-approved
  equivalent" per the page header. No dates, no per-course presenter,
  no per-course price.

Scope guarantee: by anchoring to <h2 id="dentistry">, this scraper will
never accidentally pick up biosecurity or infectious-disease courses. If
Illinois adds a new course inside the Dentistry section, it picks up
automatically. If they restructure the page (rename the dentistry h2 id,
change card markup), the scraper logs zero results — which is what we want.
"""
from __future__ import annotations

import html as html_module
import re
from decimal import Decimal
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


ILLINOIS_BASE = "https://vetmed.illinois.edu"
LISTINGS_PATH = "/ope2/online-vetmed/programs/continuing-education/"


# Matches "(24 CE Hrs)", "(3 CE Hr)", "(1 CE Hour)", "(2.5 CE Hrs)"
_RE_CE = re.compile(
    r"\(\s*(\d+(?:\.\d+)?)\s*CE\s*Hrs?\.?\s*\)",
    re.IGNORECASE,
)


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def _split_title_and_credits(raw_title: str) -> tuple[str, Decimal | None]:
    """Pull '(N CE Hrs)' out of the title text.

    Returns (clean_title, credit_hours).
    """
    if not raw_title:
        return (raw_title, None)
    m = _RE_CE.search(raw_title)
    credits: Decimal | None = None
    if m:
        try:
            credits = Decimal(m.group(1))
        except (ValueError, ArithmeticError):
            credits = None
    clean_title = _RE_CE.sub("", raw_title).strip(" -—|")
    return (clean_title, credits)


def _find_dentistry_cards(tree: HTMLParser) -> list[Node]:
    """Return every <il-clickable-card> inside the Dentistry section.

    Scoping rule: start at <h2 id="dentistry">, walk forward through the DOM,
    collect any <il-clickable-card> found until we hit the next <h2>. This
    way we never mix non-dental courses into our output, even if Illinois
    reshuffles the page.
    """
    dent_h2 = tree.css_first('h2#dentistry')
    if dent_h2 is None:
        log.warning("illinois_dentistry_section_missing")
        return []

    cards: list[Node] = []
    # selectolax doesn't expose a true sibling-walk that crosses parents, so
    # we use a flat document-order walk: iterate all elements after the h2
    # and stop at the next h2.
    all_h2 = tree.css("h2")
    next_h2: Node | None = None
    saw_dentistry = False
    for h2 in all_h2:
        if saw_dentistry:
            next_h2 = h2
            break
        if h2.attributes.get("id") == "dentistry":
            saw_dentistry = True

    # Now collect all <il-clickable-card> in the document and filter by
    # source position. selectolax preserves document order in css() results.
    for card in tree.css("il-clickable-card"):
        if _is_between(card, dent_h2, next_h2):
            cards.append(card)
    return cards


def _is_between(node: Node, start: Node, end: Node | None) -> bool:
    """True if `node` appears in document order after `start` and before `end`
    (or after `start` to EOF if end is None).

    Implementation: compare absolute byte offsets via the raw HTML positions
    selectolax exposes through Node.html. Since selectolax doesn't expose
    document-order indices directly, we fall back to comparing the node's
    serialized HTML position via a sentinel walk.
    """
    # selectolax doesn't give us absolute byte offsets, so use a different
    # strategy: walk the tree and accumulate index positions.
    # Easier: serialize start and node, compare positions in the parent's
    # html. Simplest robust approach: do a depth-first index walk.
    tree_root = start
    while tree_root.parent is not None:
        tree_root = tree_root.parent

    flat: list[Node] = []
    _flatten(tree_root, flat)
    try:
        start_idx = flat.index(start)
    except ValueError:
        return False
    try:
        node_idx = flat.index(node)
    except ValueError:
        return False
    if node_idx <= start_idx:
        return False
    if end is not None:
        try:
            end_idx = flat.index(end)
        except ValueError:
            end_idx = None
        if end_idx is not None and node_idx >= end_idx:
            return False
    return True


def _flatten(node: Node, out: list[Node]) -> None:
    """Depth-first in-order flatten."""
    out.append(node)
    for child in node.iter():
        _flatten(child, out)


def _card_to_listing(card: Node) -> RawListing | None:
    href = (card.attributes.get("href") or "").strip()
    if not href:
        return None

    h3 = card.css_first('h3[slot="header"]') or card.css_first("h3")
    title_raw = _clean(h3.text()) if h3 is not None else ""
    title, credit_hours = _split_title_and_credits(title_raw)
    if not title:
        return None

    p = card.css_first("p")
    description = _clean(p.text()) if p is not None else None

    return RawListing(
        source_slug=IllinoisDentistryScraper.SOURCE_SLUG,
        source_url=href,
        title=title,
        provider=IllinoisDentistryScraper.PROVIDER_NAME,
        description=description,
        starts_at=None,  # all on-demand
        ends_at=None,
        format="on_demand",
        cost=None,  # not on the page
        race_approved=True,  # page header asserts "RACE-approved equivalent"
        credit_hours=credit_hours,
        audience="vets and techs",  # page says open to vets + animal health professionals
        registration_url=href,
        presenter=None,  # not on the overview page
    )


class IllinoisDentistryScraper(BaseScraper):
    SOURCE_SLUG = "illinois_cvm_dentistry"
    PROVIDER_NAME = "University of Illinois CVM"
    LISTINGS_URL = f"{ILLINOIS_BASE}{LISTINGS_PATH}"
    REQUEST_DELAY = 0.0  # single fetch

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        tree = HTMLParser(listings_html)
        cards = _find_dentistry_cards(tree)
        log.info("illinois_dentistry_cards_found", count=len(cards))

        for i, card in enumerate(cards, start=1):
            listing = _card_to_listing(card)
            if listing is None:
                log.warning("illinois_card_skipped", n=i)
                continue
            log.info(
                "illinois_card_parsed",
                n=i,
                title=listing.title,
                credit_hours=str(listing.credit_hours) if listing.credit_hours else None,
                url=listing.source_url,
            )
            yield listing


if __name__ == "__main__":
    IllinoisDentistryScraper().run()