"""Integration test for the end-to-end deduplication logic.

Verifies that _mark_duplicates() correctly identifies and tags duplicate
listings with the canonical's id. Uses real Postgres via the db_session
fixture, with all changes rolled back at test end.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from vetce.models import Listing, Provider, Source
from vetce.pipeline.dedup import normalize_title
from vetce.pipeline.persist import _mark_duplicates


@pytest.fixture
def cornell_source(db_session):
    """Provide the Cornell source from the test database.

    Assumes seed has been run. If your test DB is fresh, this fixture
    will fail loudly — re-run `uv run python -m vetce.seed` first.
    """
    source = db_session.scalar(
        select(Source).where(Source.slug == "cornell_cvm_conferences")
    )
    if source is None:
        pytest.skip("cornell_cvm_conferences source missing — run seed first")
    return source


def _make_listing(
    *,
    source: Source,
    title: str,
    starts_at: date | None,
    source_url: str,
) -> Listing:
    """Build a Listing with computed normalized_title."""
    return Listing(
        source_id=source.id,
        provider_id=source.provider_id,
        source_url=source_url,
        title=title,
        normalized_title=normalize_title(title),
        starts_at=starts_at,
    )


class TestMarkDuplicates:
    def test_exact_title_and_date_match_is_marked(self, db_session, cornell_source):
        """Two listings with identical title+date should be deduplicated.

        We don't assume which of the two ends up with the lower id —
        SQLAlchemy / Postgres sequence behavior can flip insert order.
        We just assert that exactly one was marked as duplicate of the other.
        """
        row_a = _make_listing(
            source=cornell_source,
            title="Test Symposium On Dermatology",
            starts_at=date(2026, 8, 15),
            source_url="https://test.example.com/dedup-exact-a",
        )
        row_b = _make_listing(
            source=cornell_source,
            title="Test Symposium On Dermatology",
            starts_at=date(2026, 8, 15),
            source_url="https://test.example.com/dedup-exact-b",
        )
        db_session.add_all([row_a, row_b])
        db_session.flush()

        _mark_duplicates(db_session, source_slug="cornell_cvm_conferences")
        db_session.flush()
        db_session.expire_all()

        # One row should be canonical (duplicate_of=None), the other duplicate.
        # The older (lower id) is canonical.
        older, newer = sorted([row_a, row_b], key=lambda r: r.id)
        assert older.duplicate_of is None, "older row should be canonical"
        assert newer.duplicate_of == older.id, "newer row should point at older"

    def test_normalized_title_match_catches_punctuation_variants(
        self, db_session, cornell_source
    ):
        """Layer 1's normalized-title comparison catches case/punctuation
        variants that exact title matching would miss."""
        row_a = _make_listing(
            source=cornell_source,
            title="Module 1: Focus on Dermatology",
            starts_at=date(2026, 8, 15),
            source_url="https://test.example.com/dedup-norm-a",
        )
        row_b = _make_listing(
            source=cornell_source,
            title="MODULE 1 — FOCUS ON DERMATOLOGY",
            starts_at=date(2026, 8, 15),
            source_url="https://test.example.com/dedup-norm-b",
        )
        db_session.add_all([row_a, row_b])
        db_session.flush()

        _mark_duplicates(db_session, source_slug="cornell_cvm_conferences")
        db_session.flush()
        db_session.expire_all()

        older, newer = sorted([row_a, row_b], key=lambda r: r.id)
        assert older.duplicate_of is None
        assert newer.duplicate_of == older.id

    def test_different_dates_do_not_match(self, db_session, cornell_source):
        """Same title, different starts_at → not duplicates.
        Important for repeated annual events."""
        row_a = _make_listing(
            source=cornell_source,
            title="Test Annual Conference",
            starts_at=date(2026, 8, 15),
            source_url="https://test.example.com/dedup-dates-a",
        )
        row_b = _make_listing(
            source=cornell_source,
            title="Test Annual Conference",
            starts_at=date(2027, 8, 15),
            source_url="https://test.example.com/dedup-dates-b",
        )
        db_session.add_all([row_a, row_b])
        db_session.flush()

        _mark_duplicates(db_session, source_slug="cornell_cvm_conferences")
        db_session.flush()
        db_session.expire_all()

        # Neither should be marked as duplicate of the other.
        assert row_a.duplicate_of is None
        assert row_b.duplicate_of is None

    def test_canonical_row_keeps_null_duplicate_of(
        self, db_session, cornell_source
    ):
        """A non-duplicate row should never have duplicate_of set."""
        unique = _make_listing(
            source=cornell_source,
            title="Some Unique Test Title XJ47-Q9",
            starts_at=date(2026, 9, 1),
            source_url="https://test.example.com/dedup-unique",
        )
        db_session.add(unique)
        db_session.flush()

        _mark_duplicates(db_session, source_slug="cornell_cvm_conferences")
        db_session.flush()
        db_session.expire_all()

        assert unique.duplicate_of is None