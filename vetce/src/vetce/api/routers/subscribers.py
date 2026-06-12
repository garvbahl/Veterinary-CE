"""POST endpoint for newsletter signups.

Single-step opt-in: storing the email is the entire subscription flow.
Idempotent — re-submitting an existing email returns success with
already_subscribed=true, without creating a duplicate row.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from vetce.api.deps import get_session
from vetce.api.schemas import SubscriberCreate, SubscriberCreateResponse
from vetce.logging import log
from vetce.models import Subscriber


router = APIRouter(prefix="/subscribers", tags=["subscribers"])


# RFC 5322 simplified — covers the common cases without being draconian.
# Strict validation is the email server's job, not ours.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post(
    "",
    response_model=SubscriberCreateResponse,
    summary="Subscribe an email to the newsletter list",
)
def create_subscriber(
    body: SubscriberCreate,
    session: Session = Depends(get_session),
) -> SubscriberCreateResponse:
    email = body.email.strip().lower()

    if not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=400,
            detail="That doesn't look like a valid email address.",
        )

    existing = session.scalar(select(Subscriber).where(Subscriber.email == email))
    if existing is not None:
        log.info("subscriber_already_exists", email_domain=email.split("@", 1)[1])
        return SubscriberCreateResponse(ok=True, already_subscribed=True)

    subscriber = Subscriber(email=email)
    session.add(subscriber)
    session.commit()

    log.info(
        "subscriber_created",
        subscriber_id=subscriber.id,
        email_domain=email.split("@", 1)[1],
    )
    return SubscriberCreateResponse(ok=True, already_subscribed=False)