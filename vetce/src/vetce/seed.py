"""Seed script — inserts baseline Provider and Source rows.

Run with: uv run python -m vetce.seed

Idempotent: safe to run multiple times. Existing rows are left alone.
"""
from __future__ import annotations

from sqlalchemy import select

from vetce.db import SessionLocal
from vetce.logging import configure_logging, log
from vetce.models import Provider, Source


# All providers and their sources we currently support.
# As scrapers grow, add entries here.
SEED_DATA = [
    {
        "provider": {
            "slug": "vetmedteam",
            "name": "VetMedTeam",
            "website": "https://www.vetmedteam.com",
        },
        "sources": [
            {
                "slug": "vetmedteam_free",
                "kind": "scraper",
                "description": "VetMedTeam free courses listing (classes-free.aspx)",
                "cron_expression": "0 3 * * *",  # daily at 03:00 UTC
            },
        ],
    },
    {
        "provider": {
            "slug": "navta",
            "name": "NAVTA",
            "website": "https://ce.navta.net",
        },
        "sources": [
            {
                "slug": "navta_ce",
                "kind": "scraper",
                "description": "NAVTA Continuing Education home page (ce.navta.net)",
                "cron_expression": "0 3 * * *",  # daily at 03:00 UTC
            },
        ],
        
    },
    {
        "provider": {
            "slug": "cornell_cvm",
            "name": "Cornell CVM",
            "website": "https://www.vet.cornell.edu",
        },
        "sources": [
            {
                "slug": "cornell_cvm_conferences",
                "kind": "scraper",
                "description": "Cornell College of Veterinary Medicine — 2026 Conferences page",
                "cron_expression": "0 3 * * *",  # daily at 03:00 UTC
            },
        ],
    },
]


def seed() -> None:
    with SessionLocal() as session:
        for entry in SEED_DATA:
            provider_data = entry["provider"]

            # Find or create the provider.
            provider = session.scalar(
                select(Provider).where(Provider.slug == provider_data["slug"])
            )
            if provider is None:
                provider = Provider(**provider_data)
                session.add(provider)
                session.flush()  # assigns provider.id without committing
                log.info("provider_created", slug=provider.slug, id=provider.id)
            else:
                log.info("provider_exists", slug=provider.slug, id=provider.id)

            # Find or create each source under this provider.
            # Find or create each source under this provider.
            # For existing sources, refresh mutable fields (like cron_expression)
            # so changes to SEED_DATA propagate without needing a manual update.
            for source_data in entry["sources"]:
                source = session.scalar(
                    select(Source).where(Source.slug == source_data["slug"])
                )
                if source is None:
                    source = Source(provider_id=provider.id, **source_data)
                    session.add(source)
                    log.info("source_created", slug=source.slug,
                             cron=source_data.get("cron_expression"))
                else:
                    # Refresh mutable fields from seed.
                    source.cron_expression = source_data.get("cron_expression")
                    source.description = source_data.get("description")
                    log.info("source_exists", slug=source.slug, id=source.id,
                             cron=source.cron_expression)
        session.commit()
        log.info("seed_complete")


if __name__ == "__main__":
    configure_logging()
    seed()