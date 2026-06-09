"""Pipeline step: persist RawListing objects into the database.

Responsibilities:
- Resolve foreign keys (provider_id, source_id) from slugs.
- Upsert listings using source_url as the identity key.
- Maintain last_seen_at on every persist call.
- Sanitize obviously bad values before inserting.
- Mark exact-match duplicates (same title + starts_at) post-insert.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, func, literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vetce.logging import log
from vetce.models import Listing, Provider, Source
from vetce.scrapers.types import RawListing
from vetce.pipeline.dedup import normalize_title, jaccard_similarity


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
    return Decimal(str(value))


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


def persist_listing(
    session: Session,
    raw: RawListing,
    *,
    source_slug: str,
    raw_html: str | None = None,
) -> tuple[int, bool]:
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

    stmt = pg_insert(Listing).values(**values)
    update_cols = {col: stmt.excluded[col] for col in values if col != "source_url"}
    update_cols["last_seen_at"] = func.now()
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_url"],
        set_=update_cols,
    ).returning(Listing.id, literal_column("(xmax = 0)").label("is_insert"))

    result = session.execute(stmt).one()
    listing_id = result.id
    was_inserted = bool(result.is_insert)
    return listing_id, was_inserted


# Fuzzy dedup threshold. Token-Jaccard above this counts as a duplicate.
_FUZZY_THRESHOLD = 0.90


def _mark_duplicates(session: Session, source_slug: str) -> None:
    """Identify duplicates for listings from this source.

    Two-pass approach:
      Pass 1 (exact-match on normalized title): catches case/punctuation/whitespace variants.
      Pass 2 (fuzzy match via Jaccard ≥ 0.85): catches added/dropped words.

    Date handling for both passes:
      - If both rows have starts_at → dates must match exactly.
      - If both rows have starts_at IS NULL → match on title alone.
      - If asymmetric (one has, one doesn't) → don't match.

    Canonical rule: older row (lower id) wins. Newer rows get duplicate_of set.
    """
    source = session.scalar(select(Source).where(Source.slug == source_slug))
    if source is None:
        log.warning("mark_duplicates_unknown_source", source_slug=source_slug)
        return

    # Candidates: every listing from this source. (Includes on-demand rows.)
    candidates = session.scalars(
        select(Listing).where(Listing.source_id == source.id)
    ).all()

    marked_exact = 0
    marked_fuzzy = 0

    for candidate in candidates:
        canonical = _find_canonical_exact(session, candidate)
        if canonical is not None and canonical.id < candidate.id:
            if candidate.duplicate_of != canonical.id:
                candidate.duplicate_of = canonical.id
                marked_exact += 1
            continue  # Don't double-mark with fuzzy.

        canonical = _find_canonical_fuzzy(session, candidate)
        if canonical is not None and canonical.id < candidate.id:
            if candidate.duplicate_of != canonical.id:
                candidate.duplicate_of = canonical.id
                marked_fuzzy += 1
            continue

        # No match. Clear any stale link.
        if candidate.duplicate_of is not None:
            candidate.duplicate_of = None

    if marked_exact or marked_fuzzy:
        log.info(
            "duplicates_marked",
            source_slug=source_slug,
            exact=marked_exact,
            fuzzy=marked_fuzzy,
        )


def _find_canonical_exact(session: Session, candidate: Listing) -> Listing | None:
    """Find an older row matching candidate on (normalized_title, starts_at).

    Returns the oldest canonical (non-duplicate) match, or None.
    """
    if not candidate.normalized_title:
        return None

    conditions = [
        Listing.normalized_title == candidate.normalized_title,
        Listing.id != candidate.id,
        Listing.duplicate_of.is_(None),
    ]
    if candidate.starts_at is not None:
        conditions.append(Listing.starts_at == candidate.starts_at)
    else:
        conditions.append(Listing.starts_at.is_(None))

    return session.scalar(
        select(Listing)
        .where(and_(*conditions))
        .order_by(Listing.id.asc())
        .limit(1)
    )


def _find_canonical_fuzzy(session: Session, candidate: Listing) -> Listing | None:
    """Find an older row whose normalized_title has Jaccard ≥ threshold
    with the candidate's normalized_title, with matching date rules.

    Returns the oldest canonical match above threshold, or None.

    O(N) over the database. For our scale (<10k rows) this is fine; revisit
    if we ever cross that threshold.
    """
    if not candidate.normalized_title:
        return None

    # Pull all *other* canonical rows with matching date semantics.
    conditions = [
        Listing.id != candidate.id,
        Listing.duplicate_of.is_(None),
        Listing.normalized_title.is_not(None),
    ]
    if candidate.starts_at is not None:
        conditions.append(Listing.starts_at == candidate.starts_at)
    else:
        conditions.append(Listing.starts_at.is_(None))

    candidates_other = session.scalars(
        select(Listing).where(and_(*conditions)).order_by(Listing.id.asc())
    ).all()

    best_match: Listing | None = None
    best_score = 0.0
    for other in candidates_other:
        score = jaccard_similarity(
            candidate.normalized_title, other.normalized_title
        )
        if score >= _FUZZY_THRESHOLD and score > best_score:
            best_match = other
            best_score = score

    if best_match is not None:
        log.info(
            "fuzzy_match_found",
            candidate_id=candidate.id,
            canonical_id=best_match.id,
            score=round(best_score, 3),
        )
    return best_match

def persist_listings(
    session: Session,
    listings: Iterable[RawListing],
    *,
    source_slug: str,
) -> dict[str, int]:
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

    # Dedup pass: mark any new rows whose (title, starts_at) collide with
    # an existing canonical row. Runs in the same session, committed below.
    _mark_duplicates(session, source_slug=source_slug)

    session.commit()
    log.info(
        "persist_batch_complete",
        inserted=counts["inserted"],
        updated=counts["updated"],
        errors=counts["errors"],
    )
    return counts