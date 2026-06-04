"""Read endpoints for providers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vetce.api.deps import get_session
from vetce.api.schemas import ProviderOut
from vetce.models import Listing, Provider


router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderOut], summary="List all providers")
def list_providers(session: Session = Depends(get_session)) -> list[ProviderOut]:
    # Fetch providers and their listing counts in one query.
    stmt = (
        select(Provider, func.count(Listing.id).label("count"))
        .outerjoin(Listing, Listing.provider_id == Provider.id)
        .group_by(Provider.id)
        .order_by(Provider.id)
    )
    rows = session.execute(stmt).all()
    return [
        ProviderOut.from_provider(provider, listing_count=int(count))
        for provider, count in rows
    ]


@router.get(
    "/{provider_slug}",
    response_model=ProviderOut,
    summary="Fetch one provider by slug",
    responses={404: {"description": "Provider not found"}},
)
def get_provider(
    provider_slug: str,
    session: Session = Depends(get_session),
) -> ProviderOut:
    provider = session.scalar(select(Provider).where(Provider.slug == provider_slug))
    if provider is None:
        raise HTTPException(status_code=404, detail=f"Provider {provider_slug!r} not found")

    listing_count = session.scalar(
        select(func.count(Listing.id)).where(Listing.provider_id == provider.id)
    )
    return ProviderOut.from_provider(provider, listing_count=listing_count)