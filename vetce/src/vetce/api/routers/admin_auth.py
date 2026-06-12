"""Admin authentication endpoints.

Single-password admin auth. POST /admin/login with the correct password
returns a session token (also set as an HTTP-only cookie). The token is
required (via cookie) on protected /admin endpoints.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vetce.api.deps import get_session
from vetce.config import settings
from vetce.logging import log
from vetce.models import AdminSession


router = APIRouter(prefix="/admin", tags=["admin_auth"])


SESSION_COOKIE_NAME = "admin_session"
SESSION_DURATION = timedelta(days=7)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    ok: bool = True


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> LoginResponse:
    """Validate password, create a session, set the cookie."""
    # Use compare_digest to resist timing attacks. Even though we're a single
    # admin and an attacker who can time us has bigger problems, the cost of
    # doing this right is one function call.
    if not secrets.compare_digest(body.password, settings.admin_password):
        log.warning("admin_login_failed")
        # Constant 1-second delay on failed login slows brute force without
        # being annoying for the legitimate user (who types one password).
        import time
        time.sleep(1)
        raise HTTPException(status_code=401, detail="Incorrect password.")

    # Generate a 256-bit random token. URL-safe, 64 hex chars.
    token = secrets.token_hex(32)
    now = datetime.now(timezone.utc)

    admin_session = AdminSession(
        token=token,
        expires_at=now + SESSION_DURATION,
    )
    session.add(admin_session)
    session.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,    # not readable by JS — prevents XSS theft
        samesite="lax",   # not sent on cross-site POSTs — basic CSRF defense
        secure=False,     # True in production over HTTPS; False for local dev over HTTP
        path="/",
    )
    log.info("admin_login_succeeded", session_id=admin_session.id)
    return LoginResponse()


@router.post("/logout", response_model=LoginResponse)
def logout(
    response: Response,
    admin_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> LoginResponse:
    """Delete the session row and clear the cookie. Idempotent."""
    if admin_session:
        session.execute(
            delete(AdminSession).where(AdminSession.token == admin_session)
        )
        session.commit()

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    log.info("admin_logout")
    return LoginResponse()


# ----------------------------------------------------------------------
# Dependency for protecting other routes
# ----------------------------------------------------------------------

def require_admin(
    admin_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> AdminSession:
    """FastAPI dependency: raise 401 unless the request has a valid session cookie.

    Apply this to any endpoint that should be admin-only:

        @router.get("/secret")
        def my_endpoint(_: AdminSession = Depends(require_admin)):
            ...
    """
    if not admin_session:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    now = datetime.now(timezone.utc)
    row = session.scalar(
        select(AdminSession).where(AdminSession.token == admin_session)
    )

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session.")

    if row.expires_at < now:
        # Clean up expired session.
        session.delete(row)
        session.commit()
        raise HTTPException(status_code=401, detail="Session expired.")

    return row


@router.get("/me")
def get_me(_: AdminSession = Depends(require_admin)) -> dict:
    """Lightweight endpoint to check if the current session is valid.

    Used by the frontend to decide whether to redirect to login.
    """
    return {"authenticated": True}