"""FastAPI dependencies — reusable building blocks for endpoints.

Convention: each function here returns or yields something an endpoint
might want. Endpoints declare these via `Depends()` to get them injected.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from vetce.db import SessionLocal


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for the duration of one request.

    Used in endpoints like:
        def my_endpoint(session: Session = Depends(get_session)): ...

    FastAPI calls this once per request, gives the yielded session to the
    endpoint, and closes the session when the request finishes — even if
    the endpoint raised an exception.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()