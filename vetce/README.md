# PerioVive CE

A veterinary continuing education aggregation platform. Scrapes CE listings from multiple providers, deduplicates and normalizes them, and serves a unified catalog through a Next.js frontend and a FastAPI read API.

Built during an internship at Periovive Analytics.

---

## What this is

Veterinary professionals are required to complete annual CE credits, but the CE landscape is fragmented — each provider runs its own catalog with its own format, filters, and pricing. PerioVive CE pulls those catalogs into one place so vets and techs can search across providers, filter by audience and format, and find courses without bouncing between half a dozen sites.

The system currently aggregates **150+ listings across 4 providers**, with scrapers built to handle three distinct extraction patterns (HTML tables with detail pages, embedded JSON variables, and paginated card grids).

## Stack

**Backend.** Python 3.12 with [uv](https://github.com/astral-sh/uv) for dependency management. FastAPI for the read API. SQLAlchemy 2.0 + Alembic for the ORM and migrations. PostgreSQL 16 (via Docker locally). APScheduler for scheduled scraping. `httpx` + `selectolax` for HTTP and HTML parsing. `structlog` for structured logging.

**Frontend.** Next.js 16 with the App Router, TypeScript, and Tailwind CSS v4. Server components fetch from the API in parallel; URL state drives filters and sort. Inter font, custom design tokens via Tailwind v4's `@theme` directive.

## Features

- **4 working scrapers** — VetMedTeam (free courses, paginated detail pages), NAVTA (embedded JSON), Cornell CVM (text-heavy labeled lists), VetVine (paginated card grid, 115+ listings)
- **Scheduled ingestion** — APScheduler runs each source daily on a configurable cron schedule (DB-stored, per source)
- **Run history & observability** — every scrape produces a `scrape_runs` row with status, duration, and counts; survives crashes via a two-transaction durability pattern
- **Quality checks** — six SQL-based rules log warnings after each scrape (credit-hour bounds, date sanity, missing required fields, etc.)
- **Two-layer deduplication** — exact-match on normalized titles + same date; fuzzy match via token Jaccard ≥ 0.90 for case/punctuation variants
- **REST API** — pagination, multi-field filtering, sort whitelist, separate read schemas decoupled from ORM models
- **Operations dashboard** — `/admin` page surfacing health status, per-source state, and recent run history
- **Brand-consistent UI** — listings page with debounced search, URL-driven filters, mobile-responsive

## Project structure

├── alembic/ # Database migrations
├── docker-compose.yml # PostgreSQL for local dev
├── frontend/ # Next.js app
│ ├── src/app/ # Routes (App Router)
│ ├── src/components/ # Reusable React components
│ └── src/lib/ # API client, types, helpers
├── src/vetce/
│ ├── api/ # FastAPI app, routers, schemas
│ ├── models/ # SQLAlchemy models
│ ├── pipeline/ # Ingestion, persistence, dedup
│ ├── scrapers/ # Source-specific scrapers + BaseScraper
│ ├── scheduler.py # APScheduler entry point
│ ├── seed.py # Provider/source seeding
│ └── status.py # CLI health check
└── pyproject.toml # Python dependencies (managed by uv)

## Local setup

### Prerequisites

- Python 3.12, `uv` installed (`pip install uv` or [via the installer](https://docs.astral.sh/uv/))
- Node.js 20+ and `npm`
- Docker Desktop

### First-time setup

```bash
# Clone and enter
git clone https://github.com/garvbahl/Veterinary-CE.git
cd Veterinary-CE

# Backend dependencies
uv sync

# Start PostgreSQL
docker compose up -d

# Apply migrations
uv run alembic upgrade head

# Seed providers and sources
uv run python -m vetce.seed

# Run all scrapers once to populate listings
uv run python -m vetce.scrapers.sites.vetmedteam
uv run python -m vetce.scrapers.sites.navta
uv run python -m vetce.scrapers.sites.cornell_cvm
uv run python -m vetce.scrapers.sites.vetvine

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Daily development

Three terminals:

```bash
# Terminal 1: Postgres
docker compose up -d

# Terminal 2: Backend API
uv run uvicorn vetce.api.app:app --reload --port 8000

# Terminal 3: Frontend
cd frontend && npm run dev
```

Then visit:

- `http://localhost:3000` — the public site
- `http://localhost:3000/listings` — the listings catalog
- `http://localhost:3000/admin` — the operations dashboard (undocumented; no auth yet)
- `http://localhost:8000/docs` — FastAPI's auto-generated API docs

## Common operations

```bash
# Run a single scraper manually
uv run python -m vetce.scrapers.sites.<source_name>

# Check system status (CLI)
uv run python -m vetce.status

# Start the scheduler (long-running process; runs scrapers on cron)
uv run python -m vetce.scheduler

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "describe the change"

# Apply pending migrations
uv run alembic upgrade head

# Roll back the most recent migration
uv run alembic downgrade -1
```

## Adding a new scraper

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Environment variables

See `.env.example` for the full list. The most important:

- `DATABASE_URL` — PostgreSQL connection string (default points at the local Docker instance)
- `SCHEDULER_MODE` — `dev` (every 5 min, staggered) or `prod` (cron from DB)
- `NEXT_PUBLIC_API_BASE_URL` — frontend's pointer to the API (default `http://localhost:8000`)

## Status

The system has been demoed internally and is awaiting team approval before production deployment. When deployed, the plan is Railway (backend + Postgres) + Vercel (frontend).
