"""FastAPI application for the vetce read API.

Run in development with:
    uv run uvicorn vetce.api.app:app --reload --port 8000

Then visit:
    http://localhost:8000/docs       — interactive API docs (Swagger UI)
    http://localhost:8000/health     — liveness probe
    http://localhost:8000/api/v1/... — the actual API
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vetce.api.routers import admin_auth, listings, providers, runs, sources, subscribers, admin_listings
from vetce.logging import configure_logging, log


configure_logging()


# Tag descriptions improve the /docs page — they appear as section intros.
TAGS_METADATA = [
    {
        "name": "meta",
        "description": "Liveness and metadata endpoints.",
    },
    {
        "name": "listings",
        "description": (
            "CE listings aggregated from providers. Supports filtering, sorting, "
            "and pagination."
        ),
    },
    {
        "name": "providers",
        "description": "Organizations that publish CE content (universities, associations, platforms).",
    },
    {
        "name": "sources",
        "description": (
            "Individual scraped data sources. A provider can have multiple sources "
            "(e.g., a free-courses page vs. a paid-courses page)."
        ),
    },
    {
        "name": "scrape_runs",
        "description": "Operational history — every scraper invocation and its outcome.",
    },
]


app = FastAPI(
    title="Vetce API",
    description=(
        "Read API for veterinary CE listings aggregated by Vetce.\n\n"
        "All endpoints are read-only. Listings are populated by scheduled scrapers; "
        "see `/api/v1/scrape_runs` for ingestion history."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Vetce Engineering",
    },
)


import os

# CORS allowed origins. Local dev defaults are baked in; production adds
# the frontend URL via FRONTEND_URL env var.
import os
import re

# CORS allowed origins. Local dev defaults are baked in; production adds
# the frontend URL via FRONTEND_URL env var.
_cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
_frontend_url = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
if _frontend_url:
    _cors_origins.append(_frontend_url)

# Log for debugging
log.info("cors_configured", origins=_cors_origins)

# Vercel preview deployments use random subdomains under *.vercel.app.
# Match all subdomains under periovive-ce*.vercel.app for convenience.
_cors_origin_regex = r"^https://periovive-ce.*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Catch-all exception handler — return JSON instead of HTML for any uncaught error.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error(
        "api_unhandled_exception",
        path=str(request.url.path),
        method=request.method,
        error=f"{type(exc).__name__}: {exc}",
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error.",
            "error_type": type(exc).__name__,
        },
    )


# Mount routers under /api/v1.
app.include_router(listings.router,  prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(sources.router,   prefix="/api/v1")
app.include_router(runs.router,      prefix="/api/v1")
app.include_router(subscribers.router, prefix="/api/v1")
app.include_router(admin_auth.router,  prefix="/api/v1")
app.include_router(admin_listings.router, prefix="/api/v1")

@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict:
    """Returns `{ok: true}` if the process is alive."""
    return {
        "ok": True,
        "now": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.on_event("startup")
def on_startup() -> None:
    log.info("api_startup", title=app.title, version=app.version)


@app.on_event("shutdown")
def on_shutdown() -> None:
    log.info("api_shutdown")