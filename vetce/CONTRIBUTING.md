# Contributing to PerioVive CE

This document explains how to extend the system. The most common task is **adding a new scraper for a new CE provider** — that's the main focus below.

For project background and local setup, see [README.md](./README.md).

---

## Conventions

Before adding code, a few principles the codebase already follows:

- **Honest over impressive.** If a field isn't available on the source, leave it `NULL`. Don't fabricate values to make cards look fuller.
- **Pure functions where possible.** Date parsers, normalizers, similarity scorers live as module-level functions, not class methods. They're easy to test and reason about.
- **Spot-check actual database rows after scraping.** Successful insertion ≠ correct data. Log lines say "inserted 20" but you should look at the rows.
- **One scraper, one file.** `src/vetce/scrapers/sites/<provider>.py`. No multi-provider scrapers.
- **Schema separate from ORM.** Pydantic response schemas in `src/vetce/api/schemas.py` are deliberately decoupled from SQLAlchemy models. Conversion happens via `from_X()` factory methods.

---

## Adding a new scraper

The work breaks into four phases: **reconnaissance**, **seeding**, **writing**, **verifying**.

### Phase 1: Reconnaissance

Don't write code until you know the site is scrapable. Bad targets waste hours. Apply this 6-point checklist to each candidate URL:

1. **Is this the actual CE catalog?** Look for a page listing specific courses with titles, dates, registration info — not a marketing page describing the provider's CE philosophy.

2. **How many listings?** Aim for 5+ minimum, 15+ ideal.

3. **Static or JavaScript-rendered?** Right-click → View Page Source → search for a course title visible on the rendered page. If found → static (scrapable with `httpx` + `selectolax`). If not → JS-rendered (skip unless you want to introduce Playwright, which is out of scope right now).

4. **What's the data shape?**
   - Type A: All info on the listings page (no detail-page fetches). NAVTA pattern.
   - Type B: Each listing links to its own detail page with richer info. VetMedTeam pattern.
   - Type C: Embedded calendar widget from a third party (Trumba, etc). Usually JS-rendered, skip.

5. **Pagination?** Single page → simple. Multi-page → BaseScraper handles it via `list_pages()`.

6. **Bot defenses?** Cloudflare challenge, CAPTCHAs on listings URL → skip.

If a candidate clears all six, proceed. If not, find another candidate.

### Phase 2: Seed the provider and source

Open `src/vetce/seed.py`. Add an entry to `SEED_DATA`:

```python
{
    "provider": {
        "slug": "examplevet",          # lowercase, alphanumeric + underscore
        "name": "ExampleVet",           # display name for UI
        "website": "https://examplevet.com",
    },
    "sources": [
        {
            "slug": "examplevet_webinars",  # source within provider
            "kind": "scraper",
            "description": "ExampleVet on-demand webinars",
        },
    ],
},
```

Then run:

```bash
uv run python -m vetce.seed
```

Expected: `provider_created`, `source_created` log lines for your new entries. Existing rows show `provider_exists`.

### Phase 3: Write the scraper

Create `src/vetce/scrapers/sites/examplevet.py`. The pattern, with placeholders:

```python
"""Scraper for ExampleVet (examplevet.com/webinars).

Structure:
- <describe page layout: paginated cards? table? embedded JSON?>
- Fields available on listings page: <list them>
- Fields requiring detail-page fetch: <list, or "none">

Decisions:
- Detail pages: <yes/no — explain trade-off>
- Pagination: <yes/no>
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

import httpx
from selectolax.parser import HTMLParser, Node

from vetce.logging import log
from vetce.scrapers.base import BaseScraper
from vetce.scrapers.types import RawListing


class ExampleVetScraper(BaseScraper):
    SOURCE_SLUG = "examplevet_webinars"
    LISTINGS_URL = "https://examplevet.com/webinars"
    PROVIDER_NAME = "ExampleVet"

    # Only override if paginated:
    # MAX_PAGES = 30
    # def list_pages(self) -> Iterable[str]:
    #     for page in range(1, self.MAX_PAGES + 1):
    #         yield f"{self.LISTINGS_URL}?page={page}"

    def extract_listings(
        self, listings_html: str, client: httpx.Client
    ) -> Iterable[RawListing]:
        tree = HTMLParser(listings_html)
        cards = tree.css("div.your-card-selector")

        if not cards:
            log.info("examplevet_empty_page")
            return

        log.info("examplevet_cards_found", count=len(cards))

        for n, card in enumerate(cards, start=1):
            listing = _parse_card(card)
            if listing is None:
                continue
            log.info("examplevet_card_parsed", n=n, title=listing.title[:60])
            yield listing


def _parse_card(card: Node) -> RawListing | None:
    """Map one card to a RawListing. Return None to skip."""
    # ... extract title, source_url, etc.
    return RawListing(
        source_slug=ExampleVetScraper.SOURCE_SLUG,
        source_url=...,
        title=...,
        provider=ExampleVetScraper.PROVIDER_NAME,
        # Fill in what you have; leave others as None.
        description=None,
        starts_at=None,
        ends_at=None,
        format=None,
        cost=None,
        race_approved=None,
        race_program_number=None,
        credit_hours=None,
        presenter=None,
        audience=None,
        delivery_method=None,
        subject_category=None,
        topics=None,
        registration_url=None,
    )


if __name__ == "__main__":
    from vetce.logging import configure_logging
    configure_logging()
    ExampleVetScraper().run()
```

A few patterns worth noting:

- **`SOURCE_SLUG`, `LISTINGS_URL`, `PROVIDER_NAME`** are required class attributes. The base class uses them for HTTP, logging, and ingestion.
- **`list_pages()` is optional.** Default behavior fetches `LISTINGS_URL` once. Override only if the site paginates.
- **`extract_listings()` is the only required method.** Receives the HTML string and an `httpx.Client` for any detail-page fetches.
- **Don't compute `normalized_title` manually.** The persist layer handles it via `vetce.pipeline.dedup.normalize_title()`.
- **For dates/credits/etc., be defensive.** Wrap parsing in try/except, log warnings on failures, and return `None` rather than crashing.

### Phase 4: Run and verify

```bash
# Run the scraper once
uv run python -m vetce.scrapers.sites.examplevet

# Expected: "Done: {'inserted': N, 'updated': 0, 'errors': 0}"
```

**Then spot-check the data.** Don't trust the log line — look at actual rows:

```python
# Create check_examplevet.py at the project root
from sqlalchemy import select
from vetce.db import SessionLocal
from vetce.models import Listing, Provider

with SessionLocal() as s:
    provider = s.scalar(select(Provider).where(Provider.slug == "examplevet"))
    rows = list(s.scalars(
        select(Listing).where(Listing.provider_id == provider.id).limit(5)
    ).all())
    for r in rows:
        print(f"Title:    {r.title}")
        print(f"Date:     {r.starts_at}")
        print(f"Credits:  {r.credit_hours}")
        print(f"URL:      {r.source_url}")
        print("---")
```

Things to verify:

- Titles look right (not truncated, not all the same)
- Dates parsed correctly
- `source_url` is unique per row
- No fields are wildly wrong

If anything looks off, fix the parser and re-run. The scraper is idempotent — repeated runs will update existing rows in place.

Delete the check script when done:

```bash
rm check_examplevet.py
```

### Phase 5: Commit

```bash
git add src/vetce/seed.py src/vetce/scrapers/sites/examplevet.py
git commit -m "Add ExampleVet scraper (N listings)"
git push
```

That's it. The new scraper now runs daily via the scheduler with no further changes.

---

## Adding a new field to listings

Sometimes a new provider exposes a field we don't track yet (e.g., `language`, `recording_available`). Here's the migration path:

1. Add the column to `src/vetce/models/listing.py`.
2. Add the field to `RawListing` in `src/vetce/scrapers/types.py`.
3. Add the field to `persist_listing()`'s `values` dict in `src/vetce/pipeline/persist.py`.
4. Add the field to `ListingOut` and its `from_listing()` factory in `src/vetce/api/schemas.py`.
5. Add the field to the TypeScript types in `frontend/src/lib/types.ts`.
6. Update `ListingCard.tsx` and/or the detail page if the field should display.
7. Generate and run the migration:

```bash
   uv run alembic revision --autogenerate -m "add <field> to listings"
   uv run alembic upgrade head
```

All seven steps. Skipping any of them silently degrades the system.

---

## Running the test suite

```bash
uv run pytest -v
```

The suite includes:

- Unit tests for `dedup.normalize_title()` and `dedup.jaccard_similarity()`
- Unit tests for Cornell's date parsing
- Integration tests for `_mark_duplicates()` (uses local Postgres with rollback)

Integration tests assume the local database has been seeded. If you see "source missing — run seed first," run `uv run python -m vetce.seed`.

When adding new pure-function helpers, add corresponding tests under `tests/`. Integration tests should use the `db_session` fixture from `conftest.py` (transaction rolls back at test end).

---

## Frontend changes

For UI changes:

- Components live in `frontend/src/components/`.
- New routes go under `frontend/src/app/<route>/page.tsx` (App Router).
- Tailwind v4 — no `tailwind.config.ts`; theme tokens are in `frontend/src/app/globals.css` under `@theme`.
- Brand colors: `brand-*` (cyan), `ink-*` (slate), accent pink and gold.
- Buttons are pill-shaped (`rounded-pill`); cards use `shadow-card`; headings often end with a brand-cyan period (e.g., "Operations.").

Run the dev server with `cd frontend && npm run dev`. Hot-reload picks up most changes.

---

## Questions?

If something here is unclear or wrong, open an issue or update this doc. The goal is for the next person to be able to add a scraper in one focused afternoon.
