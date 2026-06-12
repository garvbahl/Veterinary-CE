"""Shared pytest fixtures for the vetce test suite.

Tests run against the local Postgres database, but each test that needs
a session gets it wrapped in a transaction that's rolled back at the end
of the test. This keeps the database clean across runs without requiring
a separate test database.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from vetce.db import SessionLocal


@pytest.fixture
def db_session() -> Session:
    """Provide a SQLAlchemy session that rolls back at test end.

    Usage:
        def test_something(db_session):
            db_session.add(SomeModel(...))
            # No need to commit — the rollback ensures isolation.
            assert ...
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()