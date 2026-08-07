"""Admin write endpoints for listings.

POST   /api/v1/admin/listings        — create a manual listing
PATCH  /api/v1/admin/listings/{id}   — edit any field on an existing listing
GET    /api/v1/admin/sources/manual  — list sources with kind='manual' (for form dropdown)

All endpoints require an admin session cookie (via require_admin).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vetce.api.deps import get_session
from vetce.api.routers.admin_auth import require_admin
from vetce.api.schemas import ListingOut
from vetce.models import AdminSession, Listing, Source


router = APIRouter(prefix="/admin", tags=["admin_listings"])


# ============================================================
# Schemas
# ============================================================

class ManualSourceOut(BaseModel):
    """Compact source representation for the form dropdown."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    provider_name: str


class ListingCreate(BaseModel):
    """Request body for POST /admin/listings."""
    source_id: int
    title: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=1000)

    # All other listing fields are optional.
    description: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    format: Optional[str] = Field(default=None, max_length=32)
    cost: Optional[str] = Field(default=None, max_length=100)
    race_approved: Optional[bool] = None
    credit_hours: Optional[Decimal] = None
    presenter: Optional[str] = Field(default=None, max_length=500)
    audience: Optional[str] = Field(default=None, max_length=64)
    registration_url: Optional[str] = Field(default=None, max_length=1000)
    subject_category: Optional[str] = Field(default=None, max_length=100)


class ListingPatch(BaseModel):
    """Request body for PATCH /admin/listings/{id}.

    Every field is optional. Only fields present in the request will be updated.
    """
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    source_url: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    description: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    format: Optional[str] = Field(default=None, max_length=32)
    cost: Optional[str] = Field(default=None, max_length=100)
    race_approved: Optional[bool] = None
    credit_hours: Optional[Decimal] = None
    presenter: Optional[str] = Field(default=None, max_length=500)
    audience: Optional[str] = Field(default=None, max_length=64)
    registration_url: Optional[str] = Field(default=None, max_length=1000)
    subject_category: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, max_length=32)
    featured: Optional[bool] = None
    featured_rank: Optional[int] = None


# ============================================================
# Endpoints
# ============================================================

@router.get(
    "/sources/manual",
    response_model=list[ManualSourceOut],
    summary="List sources with kind='manual' (for admin form dropdowns).",
)
def list_manual_sources(
    _: AdminSession = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[ManualSourceOut]:
    stmt = (
        select(Source)
        .where(Source.kind == "manual")
        .options(selectinload(Source.provider))
        .order_by(Source.slug)
    )
    rows = session.scalars(stmt).all()
    return [
        ManualSourceOut(
            id=s.id,
            slug=s.slug,
            provider_name=s.provider.name,
        )
        for s in rows
    ]


@router.post(
    "/listings",
    response_model=ListingOut,
    status_code=201,
    summary="Create a new listing manually.",
)
def create_listing(
    body: ListingCreate,
    _: AdminSession = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ListingOut:
    # Validate the source exists and is manual-kind.
    source = session.scalar(select(Source).where(Source.id == body.source_id))
    if source is None:
        raise HTTPException(status_code=400, detail="Source not found.")
    if source.kind != "manual":
        raise HTTPException(
            status_code=400,
            detail=f"Source '{source.slug}' is not a manual source.",
        )

    # source_url must be unique. Reject duplicates upfront with a helpful error.
    existing = session.scalar(
        select(Listing).where(Listing.source_url == body.source_url)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A listing already exists with this source_url (id={existing.id}).",
        )

    listing = Listing(
        provider_id=source.provider_id,
        source_id=source.id,
        source_url=body.source_url,
        title=body.title,
        description=body.description,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        format=body.format,
        cost=body.cost,
        race_approved=body.race_approved,
        credit_hours=body.credit_hours,
        presenter=body.presenter,
        audience=body.audience,
        registration_url=body.registration_url,
        subject_category=body.subject_category,
        status="active",
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)

    # Reload with relationships for the response.
    listing = session.scalar(
        select(Listing)
        .where(Listing.id == listing.id)
        .options(
            selectinload(Listing.provider),
            selectinload(Listing.source),
        )
    )
    return ListingOut.from_listing(listing)


@router.patch(
    "/listings/{listing_id}",
    response_model=ListingOut,
    summary="Update one or more fields on an existing listing.",
)
def update_listing(
    listing_id: int,
    body: ListingPatch,
    _: AdminSession = Depends(require_admin),
    session: Session = Depends(get_session),
) -> ListingOut:
    listing = session.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found.")

    # Apply only the fields explicitly set in the request.
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(listing, key, value)

    session.commit()
    session.refresh(listing)

    listing = session.scalar(
        select(Listing)
        .where(Listing.id == listing.id)
        .options(
            selectinload(Listing.provider),
            selectinload(Listing.source),
        )
    )
    return ListingOut.from_listing(listing)

@router.get(
    "/listings",
    response_model=list[ListingOut],
    summary="List all listings for admin view (bypasses public filters).",
)
def list_listings_admin(
    limit: int = 50,
    _: AdminSession = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[ListingOut]:
    stmt = (
        select(Listing)
        .options(
            selectinload(Listing.provider),
            selectinload(Listing.source),
        )
        .order_by(Listing.id.desc())
        .limit(limit)
    )
    rows = session.scalars(stmt).all()
    return [ListingOut.from_listing(l) for l in rows]