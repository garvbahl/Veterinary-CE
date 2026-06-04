"""Read endpoints for scrape_runs — operational visibility over HTTP."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vetce.api.deps import get_session
from vetce.api.schemas import ScrapeRunOut
from vetce.models import ScrapeRun, Source


router = APIRouter(prefix="/scrape_runs", tags=["scrape_runs"])


@router.get(
    "",
    response_model=list[ScrapeRunOut],
    summary="List recent scrape runs (most recent first)",
)
def list_scrape_runs(
    limit: int = Query(default=20, ge=1, le=100),
    source: str | None = Query(default=None, description="Optional source slug filter"),
    status: str | None = Query(
        default=None,
        description="Optional status filter: success | partial | failed | running",
    ),
    session: Session = Depends(get_session),
) -> list[ScrapeRunOut]:
    stmt = (
        select(ScrapeRun)
        .options(selectinload(ScrapeRun.source))
        .order_by(ScrapeRun.started_at.desc())
    )
    if source:
        stmt = stmt.join(Source, ScrapeRun.source_id == Source.id).where(Source.slug == source)
    if status:
        stmt = stmt.where(ScrapeRun.status == status)
    stmt = stmt.limit(limit)
    runs = session.scalars(stmt).all()
    return [ScrapeRunOut.from_scrape_run(r) for r in runs]