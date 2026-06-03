"""Operational status report.

Run with:
    uv run python -m vetce.status

Designed to answer "is everything okay?" at a glance. Shows:
  - Per-source summary (cron, listing count, last run status)
  - Recent scrape_runs across all sources
  - Open quality issues
  - Zombie run warnings

Output is plain text, designed for human reading in a terminal.
Not designed for parsing — use SQL for that.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select

from vetce.db import SessionLocal
from vetce.logging import configure_logging
from vetce.models import Listing, ScrapeRun, Source
from vetce.quality import run_checks


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "(running)"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    rem = seconds % 60
    return f"{minutes}m {rem:.0f}s"


def _format_age(when: datetime | None) -> str:
    if when is None:
        return "never"
    delta = datetime.now(timezone.utc) - when
    total = delta.total_seconds()
    if total < 60:
        return f"{int(total)}s ago"
    if total < 3600:
        return f"{int(total // 60)}m ago"
    if total < 86400:
        return f"{int(total // 3600)}h ago"
    return f"{int(total // 86400)}d ago"


def _print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def _per_source_summary() -> None:
    _print_header("Per-Source Summary")
    with SessionLocal() as s:
        sources = list(s.scalars(select(Source).order_by(Source.id)).all())
        for source in sources:
            listing_count = s.scalar(
                select(func.count(Listing.id)).where(Listing.source_id == source.id)
            )
            last_run = s.scalar(
                select(ScrapeRun)
                .where(ScrapeRun.source_id == source.id)
                .order_by(ScrapeRun.started_at.desc())
                .limit(1)
            )
            print(f"\n  {source.slug}")
            print(f"    cron:          {source.cron_expression or '(not scheduled)'}")
            print(f"    listings:      {listing_count}")
            if last_run:
                print(f"    last run:      {_format_age(last_run.started_at)} "
                      f"(status={last_run.status})")
                if last_run.error_message:
                    print(f"    last error:    {last_run.error_message}")
            else:
                print(f"    last run:      never")


def _recent_runs() -> None:
    _print_header("Recent Scrape Runs (last 10)")
    with SessionLocal() as s:
        rows = list(s.scalars(
            select(ScrapeRun)
            .order_by(ScrapeRun.started_at.desc())
            .limit(10)
        ).all())
        if not rows:
            print("\n  No scrape runs recorded yet.")
            return
        for r in rows:
            source = s.get(Source, r.source_id)
            duration = (
                (r.finished_at - r.started_at).total_seconds()
                if r.finished_at else None
            )
            status_indicator = {
                "success": "✓",
                "partial": "~",
                "failed":  "✗",
                "running": "…",
            }.get(r.status, "?")
            print(f"\n  [{status_indicator}] run {r.id}: {source.slug}")
            print(f"      started:   {_format_age(r.started_at)}")
            print(f"      duration:  {_format_duration(duration)}")
            print(f"      counts:    +{r.listings_inserted} ~{r.listings_updated} "
                  f"errors={r.listings_errored}")
            if r.error_message:
                print(f"      error:     {r.error_message}")


def _quality_summary() -> None:
    _print_header("Quality Checks")
    issues = run_checks()
    if not issues:
        print("\n  ✓ All checks passed.")
        return
    print(f"\n  ⚠ {len(issues)} issue(s) found:")
    for i in issues:
        print(f"\n    [{i.severity}] {i.check_name} ({i.source_slug or 'all'})")
        print(f"      {i.message}")
        if i.sample_ids:
            print(f"      sample listing ids: {i.sample_ids}")


def main() -> None:
    # Suppress the structlog setup output so the report looks clean.
    # We're writing plain text for humans, not JSON for machines.
    configure_logging()

    print()
    print(f"vetce status — {datetime.now(timezone.utc).isoformat(timespec='seconds')}")

    _per_source_summary()
    _recent_runs()
    _quality_summary()

    print()


if __name__ == "__main__":
    main()