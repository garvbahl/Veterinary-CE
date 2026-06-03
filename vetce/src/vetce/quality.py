"""SQL-based data quality checks.

Runs after each scrape (and on demand) to detect:
  - Per-listing sanity violations (impossible credit_hours, bad dates, etc.)
  - Per-source drift (sudden drops in row count or field-population rates)
  - System-wide health (zombie runs, missing scrapers)

Design principle: checks are NON-BLOCKING. A failed check logs a warning;
it does NOT roll back data or kill the scrape. The point is detection,
not enforcement.

Add a new check by writing a function with this signature:
    def check_X(session, source_slug: str | None = None) -> Iterable[QualityIssue]

Then add it to ALL_CHECKS at the bottom of the file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from vetce.db import SessionLocal
from vetce.logging import log
from vetce.models import Listing, Provider, ScrapeRun, Source


@dataclass
class QualityIssue:
    """One thing the system noticed that may be wrong."""
    check_name: str
    severity: str               # "warning" | "error"
    source_slug: str | None     # which source it's about (None = global)
    message: str                # human-readable summary
    count: int = 0              # how many rows triggered this check
    sample_ids: list[int] | None = None  # up to 5 example listing IDs

    def as_log_kwargs(self) -> dict:
        """Convert to keyword args suitable for structlog."""
        return {
            "check": self.check_name,
            "severity": self.severity,
            "source": self.source_slug or "(all)",
            "count": self.count,
            "samples": self.sample_ids or [],
            "msg": self.message,
        }


# ===== Category 1: Per-listing sanity rules =====

def check_implausible_credit_hours(
    session: Session, source_slug: str | None = None
) -> Iterable[QualityIssue]:
    """Credit hours over 50 are almost certainly a parsing bug."""
    stmt = select(Listing.id).where(Listing.credit_hours > 50)
    if source_slug:
        stmt = stmt.join(Source).where(Source.slug == source_slug)
    bad_ids = list(session.scalars(stmt).all())
    if bad_ids:
        yield QualityIssue(
            check_name="implausible_credit_hours",
            severity="warning",
            source_slug=source_slug,
            message=f"{len(bad_ids)} listing(s) have credit_hours > 50 — likely a parsing bug",
            count=len(bad_ids),
            sample_ids=bad_ids[:5],
        )


def check_inverted_dates(
    session: Session, source_slug: str | None = None
) -> Iterable[QualityIssue]:
    """starts_at must be on or before ends_at."""
    stmt = select(Listing.id).where(
        and_(
            Listing.starts_at.is_not(None),
            Listing.ends_at.is_not(None),
            Listing.starts_at > Listing.ends_at,
        )
    )
    if source_slug:
        stmt = stmt.join(Source).where(Source.slug == source_slug)
    bad_ids = list(session.scalars(stmt).all())
    if bad_ids:
        yield QualityIssue(
            check_name="inverted_dates",
            severity="error",
            source_slug=source_slug,
            message=f"{len(bad_ids)} listing(s) have starts_at > ends_at",
            count=len(bad_ids),
            sample_ids=bad_ids[:5],
        )


def check_negative_credit_hours(
    session: Session, source_slug: str | None = None
) -> Iterable[QualityIssue]:
    """Credit hours below zero are impossible."""
    stmt = select(Listing.id).where(Listing.credit_hours < 0)
    if source_slug:
        stmt = stmt.join(Source).where(Source.slug == source_slug)
    bad_ids = list(session.scalars(stmt).all())
    if bad_ids:
        yield QualityIssue(
            check_name="negative_credit_hours",
            severity="error",
            source_slug=source_slug,
            message=f"{len(bad_ids)} listing(s) have negative credit_hours",
            count=len(bad_ids),
            sample_ids=bad_ids[:5],
        )


def check_suspicious_titles(
    session: Session, source_slug: str | None = None
) -> Iterable[QualityIssue]:
    """Titles that look like scraper bugs rather than course names."""
    SUSPICIOUS_PATTERNS = [
        "click here",
        "view details",
        "your browser",
        "additional training",  # Cornell Sim Lab style — we filter these
                                 # but if one slipped through, we want to know
        "404",
        "error",
    ]
    bad_ids: list[int] = []
    for pattern in SUSPICIOUS_PATTERNS:
        stmt = select(Listing.id).where(
            func.lower(Listing.title).like(f"%{pattern}%")
        )
        if source_slug:
            stmt = stmt.join(Source).where(Source.slug == source_slug)
        bad_ids.extend(session.scalars(stmt).all())

    # Also flag very long titles (likely too much page text was captured).
    long_title_stmt = select(Listing.id).where(func.length(Listing.title) > 300)
    if source_slug:
        long_title_stmt = long_title_stmt.join(Source).where(Source.slug == source_slug)
    bad_ids.extend(session.scalars(long_title_stmt).all())

    bad_ids = list(set(bad_ids))  # de-dup if a title matched multiple patterns
    if bad_ids:
        yield QualityIssue(
            check_name="suspicious_titles",
            severity="warning",
            source_slug=source_slug,
            message=f"{len(bad_ids)} listing(s) have titles that look like scraper bugs",
            count=len(bad_ids),
            sample_ids=bad_ids[:5],
        )


# ===== Category 2: Per-source drift detection =====

def check_row_count_drop(
    session: Session, source_slug: str | None = None
) -> Iterable[QualityIssue]:
    """If a recent run produced far fewer rows than its predecessors, alert.

    Looks at the most recent successful run for each source and compares its
    total to the median of the previous 5 runs. If the new run is <50% of
    the median, that's suspicious.
    """
    sources_to_check = []
    if source_slug:
        s = session.scalar(select(Source).where(Source.slug == source_slug))
        if s:
            sources_to_check = [s]
    else:
        sources_to_check = list(session.scalars(select(Source)).all())

    for source in sources_to_check:
        recent_runs = list(session.scalars(
            select(ScrapeRun)
            .where(
                and_(
                    ScrapeRun.source_id == source.id,
                    ScrapeRun.status.in_(["success", "partial"]),
                )
            )
            .order_by(ScrapeRun.started_at.desc())
            .limit(6)
        ).all())

        if len(recent_runs) < 3:
            # Not enough history to spot drift yet.
            continue

        latest = recent_runs[0]
        prior = recent_runs[1:]
        latest_total = latest.listings_inserted + latest.listings_updated
        prior_totals = [r.listings_inserted + r.listings_updated for r in prior]
        prior_totals.sort()
        median_prior = prior_totals[len(prior_totals) // 2]

        if median_prior > 0 and latest_total < median_prior * 0.5:
            yield QualityIssue(
                check_name="row_count_drop",
                severity="warning",
                source_slug=source.slug,
                message=(
                    f"Most recent {source.slug} run produced {latest_total} rows, "
                    f"vs median of {median_prior} from prior runs — possible regression"
                ),
                count=1,
            )


# ===== Category 3: System-wide health =====

def check_zombie_runs(
    session: Session, source_slug: str | None = None
) -> Iterable[QualityIssue]:
    """scrape_runs rows stuck in 'running' for over an hour are zombies.

    Possible causes: process crashed, machine rebooted, lost connection to DB
    mid-write. Either way, the row needs a human's attention.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    stmt = select(ScrapeRun.id).where(
        and_(
            ScrapeRun.status == "running",
            ScrapeRun.started_at < cutoff,
        )
    )
    if source_slug:
        stmt = stmt.join(Source).where(Source.slug == source_slug)
    zombie_ids = list(session.scalars(stmt).all())
    if zombie_ids:
        yield QualityIssue(
            check_name="zombie_runs",
            severity="error",
            source_slug=source_slug,
            message=(
                f"{len(zombie_ids)} scrape_run(s) have been in 'running' state "
                f"for over 1 hour — likely crashed processes"
            ),
            count=len(zombie_ids),
            sample_ids=zombie_ids[:5],
        )


# ===== The registry =====

ALL_CHECKS: list[Callable[[Session, str | None], Iterable[QualityIssue]]] = [
    check_implausible_credit_hours,
    check_inverted_dates,
    check_negative_credit_hours,
    check_suspicious_titles,
    check_row_count_drop,
    check_zombie_runs,
]


def run_checks(source_slug: str | None = None) -> list[QualityIssue]:
    """Run all quality checks. Returns a list of issues found.

    If source_slug is provided, each check filters to that source only.
    If None, checks run across all sources.
    """
    issues: list[QualityIssue] = []
    with SessionLocal() as session:
        for check_fn in ALL_CHECKS:
            check_issues = list(check_fn(session, source_slug))
            for issue in check_issues:
                log.warning("quality_issue", **issue.as_log_kwargs())
                issues.append(issue)
    return issues


def main() -> None:
    """CLI entry point: run all checks against all data and report."""
    from vetce.logging import configure_logging
    configure_logging()
    log.info("quality_checks_starting")
    issues = run_checks()
    if not issues:
        log.info("quality_checks_clean", checks_run=len(ALL_CHECKS))
        print(f"\nAll {len(ALL_CHECKS)} checks passed. ✓")
    else:
        log.info("quality_checks_complete",
                 checks_run=len(ALL_CHECKS),
                 issues_found=len(issues))
        print(f"\n{len(issues)} issue(s) found across {len(ALL_CHECKS)} checks. See log output above.")


if __name__ == "__main__":
    main()