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
    {
        "provider": {
            "slug": "vetvine",
            "name": "VetVine",
            "website": "https://www.vetvine.com",
        },
        "sources": [
            {
                "slug": "vetvine_videos_on_demand",
                "kind": "scraper",
                "description": "VetVine Videos on Demand catalog (paginated)",
            },
        ],
    },
    {
        "provider": {
            "slug": "periovive",
            "name": "Periovive",
            "website": "https://www.periovive.com",
        },
        "sources": [
            {
                "slug": "periovive_webinars",
                "kind": "scraper",
                "description": "Periovive upcoming webinars listing (periovive.com/webinars)",
                "cron_expression": "0 3 * * *",  # daily at 03:00 UTC
            },
            {
                "slug": "periovive_thinkific",
                "kind": "scraper",
                "description": "Periovive Thinkific course catalog (periovive.thinkific.com/collections)",
                "cron_expression": "0 3 * * *",
            },
        ],
    },
    {
        "provider": {
            "slug": "midmark",
            "name": "Midmark Academy",
            "website": "https://www.midmark.com/animal-health/education-services-support/midmark-academy-clinical-training/course-offerings",
        },
        "sources": [
            {
                "slug": "midmark_manual",
                "kind": "manual",
                "description": "Midmark Academy online dental CE courses (manually curated from midmark2.abaralms.net)",
                "cron_expression": None,
            },
        ],
    },
    {
        "provider": {
            "slug": "pawsitive",
            "name": "Pawsitive Dental Education",
            "website": "https://pawsitivedental.com",
        },
        "sources": [
            {
                "slug": "pawsitive_manual",
                "kind": "manual",
                "description": "Pawsitive Dental Education events (manually curated from pawsitivedental.com)",
                "cron_expression": None,
            },
        ],
    },
    {
    "provider": {
        "slug": "adtc",
        "name": "Animal Dental Training Center",
        "website": "https://www.animaldentaltraining.com",
    },
    "sources": [
        {
            "slug": "adtc_courses",
            "kind": "scraper",
            "description": "ADTC veterinary dental CE courses (animaldentaltraining.com)",
            "cron_expression": "0 3 * * *",
        },
    ],
},
    {
    "provider": {
        "slug": "silo_academy",
        "name": "Silo Academy",
        "website": "https://siloacademy.com",
    },
    "sources": [
        {
            "slug": "silo_academy_manual",
            "kind": "manual",
            "description": "Manual entries for Silo Academy CE courses (siloacademy.com)",
            "cron_expression": None,
        },
    ],
},
{
    "provider": {
        "slug": "manual_misc",
        "name": "Other",
        "website": None,
    },
    "sources": [
        {
            "slug": "manual_misc",
            "kind": "manual",
            "description": "Catch-all manual entries (for orgs without a dedicated source).",
            "cron_expression": None,
        },
    ],
},
    {
        "provider": {
            "slug": "avdc",
            "name": "American Veterinary Dental College",
            "website": "https://avdc.org",
        },
        "sources": [
            {
                "slug": "avdc_events",
                "kind": "scraper",
                "description": "AVDC continuing education events (avdc.org/events)",
                "cron_expression": "0 3 * * *",  # daily at 03:00 UTC
            },
        ],
    },
    {
       "provider": {
           "slug": "animal_dental_care_co",
           "name": "Animal Dental Care & Oral Surgery",
           "website": "https://vetdentalclasses.com",
       },
       "sources": [
           {
               "slug": "animal_dental_care_manual",
               "kind": "manual",
               "description": "Manual entries for Animal Dental Care & Oral Surgery (Colorado).",
               "cron_expression": None,
           },
           {
                "slug": "vetdentalclasses",
                "kind": "scraper",
                "description": "Vet Dental Classes -- Dr. Patrick Vall DAVDC, Colorado Springs (WordPress course pages, dated wet labs).",
                "cron_expression": "0 3 * * *",
            },
        ],
    },
    {
    "provider": {
        "slug": "crown_vet_dentistry",
        "name": "Crown Veterinary Dental Specialists",
        "website": "https://crownvetdentistry.com",
    },
    "sources": [
        {
            "slug": "crown_vet_dentistry",
            "kind": "scraper",
            "description": "Crown Veterinary Dental Specialists CE courses (Charlotte, NC)",
            "cron_expression": "0 3 * * *",
        },
    ],
},
    {
        "provider": {
            "slug": "vdspets",
            "name": "Veterinary Dental Specialties",
            "website": "https://www.vdspets.com",
        },
        "sources": [
            {
                "slug": "vdspets",
                "kind": "scraper",
                "description": "Veterinary Dental Specialties -- Dr. Brook Niemiec, hands-on wet labs across US locations (WooCommerce Store API, upcoming-only).",
                "cron_expression": "0 3 * * *",
            },
        ],
    },
    {
        "provider": {
            "slug": "tufts_cummings",
            "name": "Tufts Cummings School of Veterinary Medicine",
            "website": "https://vet.tufts.edu/continuing-education-programs",
        },
        "sources": [
            {
                "slug": "tufts_vet_ce",
                "kind": "scraper",
                "description": "Tufts Cummings vet CE (Canvas Catalog public JSON, dental-filtered by tagger).",
                "cron_expression": "0 3 * * *",
            },
        ],
    },
    {
    "provider": {
        "slug": "vetfolio",
        "name": "VetFolio",
        "website": "https://www.vetfolio.com",
    },
    "sources": [
        {
            "slug": "vetfolio_manual",
            "kind": "manual",
            "description": "Manual entries for VetFolio dental courses (powered by NAVC & VMX).",
            "cron_expression": None,
        },
        {
            "slug": "vetfolio_catalog",
            "kind": "scraper",
            "description": "VetFolio dental CE catalog (Thought Industries browse API, dental-filtered).",
            "cron_expression": "0 3 * * *",
        },
    ],
},
    {
    "provider": {
        "slug": "vetandtech",
        "name": "Vet and Tech",
        "website": "https://www.vetandtech.com",
    },
    "sources": [
        {
            "slug": "vetandtech_webinars",
            "kind": "scraper",
            "description": "Vet and Tech RACE-approved veterinary webinars (Next.js __NEXT_DATA__, dental-filtered).",
            "cron_expression": "0 3 * * *",
        },
    ],
},
    {
    "provider": {
        "slug": "illinois_cvm",
        "name": "University of Illinois CVM",
        "website": "https://vetmed.illinois.edu",
    },
    "sources": [
        {
            "slug": "illinois_cvm_dentistry",
            "kind": "scraper",
            "description": "University of Illinois College of Veterinary Medicine — Dentistry CE catalog",
            "cron_expression": "0 3 * * *",
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