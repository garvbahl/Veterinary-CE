"""Pipeline step: persist RawListing objects into the database.

Responsibilities:
- Resolve foreign keys (provider_id, source_id) from slugs.
- Upsert listings using source_url as the identity key.
- Maintain last_seen_at on every persist call.
- Sanitize obviously bad values before inserting.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select, func, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vetce.logging import log
from vetce.models import Provider, Source, Listing
from vetce.scrapers.types import RawListing


# RACE program numbers are typically 6-7 digits. Anything else is suspect.
_VALID_RACE_NUMBER = re.compile(r"^\d{4,8}$")


def _sanitize_race_number(value: str | None) -> str | None:
    """Drop placeholder / non-numeric program numbers like 'UPDATE' or 'TBD'."""
    if value is None:
        return None
    if _VALID_RACE_NUMBER.match(value.strip()):
        return value.strip()
    log.warning("race_program_number_rejected", value=value)
    return None


def _to_decimal(value: float | int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))  # via str() to avoid float-binary noise


def _hash_html(html: str | None) -> str | None:
    if not html:
        return None
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def _resolve_provider(session: Session, name: str) -> Provider:
    """Find a Provider by name. Raises if not seeded."""
    provider = session.scalar(select(Provider).where(Provider.name == name))
    if provider is None:
        raise ValueError(
            f"Provider {name!r} not found in database. "
            f"Run `python -m vetce.seed` first."
        )
    return provider


def _resolve_source(session: Session, slug: str) -> Source:
    """Find a Source by slug. Raises if not seeded."""
    source = session.scalar(select(Source).where(Source.slug == slug))
    if source is None:
        raise ValueError(
            f"Source {slug!r} not found in database. "
            f"Run `python -m vetce.seed` first."
        )
    return source


def persist_listing(session: Session, raw: RawListing, *,
                    source_slug: str, raw_html: str | None = None) -> tuple[int, bool]:
    """Upsert a single RawListing into the database.

    Returns (listing_id, was_inserted). was_inserted is True if a new row was
    created, False if an existing row was updated.
    """
    provider = _resolve_provider(session, raw.provider)
    source = _resolve_source(session, source_slug)

    values = {
        "provider_id": provider.id,
        "source_id": source.id,
        "source_url": raw.source_url,
        "title": raw.title,
        "description": raw.description,
        "starts_at": raw.starts_at,
        "ends_at": raw.ends_at,
        "format": raw.format,
        "cost": raw.cost,
        "race_approved": raw.race_approved,
        "race_program_number": _sanitize_race_number(raw.race_program_number),
        "credit_hours": _to_decimal(float(raw.credit_hours)) if raw.credit_hours is not None else None,
        "presenter": raw.presenter,
        "audience": raw.audience,
        "delivery_method": raw.delivery_method,
        "subject_category": raw.subject_category,
        "topics": raw.topics or [],
        "registration_url": raw.registration_url,
        "raw_html": raw_html,
        "raw_html_hash": _hash_html(raw_html),
        "status": "active",
    }

    from sqlalchemy import literal_column

    stmt = pg_insert(Listing).values(**values)
    update_cols = {col: stmt.excluded[col] for col in values if col != "source_url"}
    update_cols["last_seen_at"] = func.now()  # explicit; don't rely on excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_url"],
        set_=update_cols,
    ).returning(Listing.id, literal_column("(xmax = 0)").label("is_insert"))

    result = session.execute(stmt).one()
    listing_id = result.id
    was_inserted = bool(result.is_insert)
    return listing_id, was_inserted


def persist_listings(session: Session, listings: Iterable[RawListing], *,
                     source_slug: str) -> dict[str, int]:
    """Persist a batch of listings. Returns counts of inserts/updates/errors."""
    counts = {"inserted": 0, "updated": 0, "errors": 0}
    for raw in listings:
        try:
            _id, was_inserted = persist_listing(session, raw, source_slug=source_slug)
            if was_inserted:
                counts["inserted"] += 1
            else:
                counts["updated"] += 1
        except Exception as e:
            log.warning("persist_failed", source_url=raw.source_url, error=str(e))
            counts["errors"] += 1
    session.commit()
    log.info("persist_batch_complete", **counts)
    return counts