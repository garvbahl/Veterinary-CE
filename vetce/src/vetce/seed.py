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
            for source_data in entry["sources"]:
                source = session.scalar(
                    select(Source).where(Source.slug == source_data["slug"])
                )
                if source is None:
                    source = Source(provider_id=provider.id, **source_data)
                    session.add(source)
                    log.info("source_created", slug=source.slug)
                else:
                    log.info("source_exists", slug=source.slug, id=source.id)

        session.commit()
        log.info("seed_complete")


if __name__ == "__main__":
    configure_logging()
    seed()