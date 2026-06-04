"""Read endpoints for CE listings.

GET /api/v1/listings        — list listings with pagination/filtering/sorting
GET /api/v1/listings/{id}   — fetch one listing by id
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from vetce.api.deps import get_session
from vetce.api.schemas import ListingOut, ListingsPage
from vetce.models import Listing, Provider, Source


router = APIRouter(prefix="/listings", tags=["listings"])


# Whitelist of fields a client is allowed to sort by. Anything else → 400.
# (Don't accept arbitrary column names from the client — that opens the door
# to information leaks and surprising errors.)
SORTABLE_FIELDS = {
    "id": Listing.id,
    "title": Listing.title,
    "starts_at": Listing.starts_at,
    "credit_hours": Listing.credit_hours,
}


@router.get(
    "",
    response_model=ListingsPage,
    summary="List listings with filtering, sorting, and pagination",
)
def list_listings(
    # --- pagination ---
    limit: int = Query(default=20, ge=1, le=100,
                       description="How many to return. Max 100."),
    offset: int = Query(default=0, ge=0,
                        description="How many to skip (for paging)."),
    # --- filtering ---
    provider: str | None = Query(
        default=None,
        description="Provider slug (e.g. 'navta'). Matches exact slug.",
    ),
    source: str | None = Query(
        default=None,
        description="Source slug (e.g. 'navta_ce').",
    ),
    audience: str | None = Query(
        default=None,
        description="Filter by audience: 'vets', 'techs', 'vets and techs'.",
    ),
    format: str | None = Query(
        default=None,
        description="Filter by format: 'live', 'on_demand', 'hybrid'.",
    ),
    min_credits: float | None = Query(
        default=None, ge=0,
        description="Only listings with credit_hours >= this value.",
    ),
    max_credits: float | None = Query(
        default=None, ge=0,
        description="Only listings with credit_hours <= this value.",
    ),
    q: str | None = Query(
        default=None, min_length=2, max_length=100,
        description="Free-text search over title and description.",
    ),
    # --- sorting ---
    sort: Literal["id", "title", "starts_at", "credit_hours"] = Query(
        default="id",
        description="Field to sort by.",
    ),
    order: Literal["asc", "desc"] = Query(
        default="asc",
        description="Sort direction.",
    ),
    # --- dependencies ---
    session: Session = Depends(get_session),
) -> ListingsPage:
    # Start building the query. Eager-load relationships so the Pydantic
    # factory doesn't trigger N+1 queries.
    stmt = (
        select(Listing)
        .options(
            selectinload(Listing.provider),
            selectinload(Listing.source),
        )
    )

    # Apply filters. Each becomes an additional WHERE clause if present.
    conditions = []

    if provider:
        # provider is the slug; we have to join through Provider.
        stmt = stmt.join(Provider, Listing.provider_id == Provider.id)
        conditions.append(Provider.slug == provider)

    if source:
        stmt = stmt.join(Source, Listing.source_id == Source.id)
        conditions.append(Source.slug == source)

    if audience:
        conditions.append(Listing.audience == audience)

    if format:
        conditions.append(Listing.format == format)

    if min_credits is not None:
        conditions.append(Listing.credit_hours >= min_credits)

    if max_credits is not None:
        conditions.append(Listing.credit_hours <= max_credits)

    if q:
        # Case-insensitive search across title and description.
        pattern = f"%{q}%"
        conditions.append(
            (Listing.title.ilike(pattern)) | (Listing.description.ilike(pattern))
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Count BEFORE applying limit/offset, so the total reflects the filtered set.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.scalar(count_stmt) or 0

    # Apply sorting.
    sort_column = SORTABLE_FIELDS[sort]
    stmt = stmt.order_by(
        sort_column.desc() if order == "desc" else sort_column.asc()
    )

    # Apply pagination.
    stmt = stmt.limit(limit).offset(offset)

    listings = session.scalars(stmt).all()

    return ListingsPage(
        items=[ListingOut.from_listing(l) for l in listings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{listing_id}",
    response_model=ListingOut,
    summary="Fetch one listing by id",
    responses={404: {"description": "Listing not found"}},
)
def get_listing(
    listing_id: int,
    session: Session = Depends(get_session),
) -> ListingOut:
    stmt = (
        select(Listing)
        .where(Listing.id == listing_id)
        .options(
            selectinload(Listing.provider),
            selectinload(Listing.source),
        )
    )
    listing = session.scalar(stmt)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    return ListingOut.from_listing(listing)