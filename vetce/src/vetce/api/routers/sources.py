"""Read endpoints for sources."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from vetce.api.deps import get_session
from vetce.api.schemas import SourceOut
from vetce.models import Listing, Source


router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut], summary="List all sources")
def list_sources(session: Session = Depends(get_session)) -> list[SourceOut]:
    sources = session.scalars(
        select(Source).options(selectinload(Source.provider)).order_by(Source.id)
    ).all()
    out: list[SourceOut] = []
    for source in sources:
        count = session.scalar(
            select(func.count(Listing.id)).where(Listing.source_id == source.id)
        )
        out.append(SourceOut.from_source(source, listing_count=count))
    return out


@router.get(
    "/{source_slug}",
    response_model=SourceOut,
    summary="Fetch one source by slug",
    responses={404: {"description": "Source not found"}},
)
def get_source(
    source_slug: str,
    session: Session = Depends(get_session),
) -> SourceOut:
    source = session.scalar(
        select(Source)
        .where(Source.slug == source_slug)
        .options(selectinload(Source.provider))
    )
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source {source_slug!r} not found")
    count = session.scalar(
        select(func.count(Listing.id)).where(Listing.source_id == source.id)
    )
    return SourceOut.from_source(source, listing_count=count)