"""Batch-tag all untagged listings with subject categories.

Run with:
    uv run python -m vetce.pipeline.tag_all
    uv run python -m vetce.pipeline.tag_all --limit 10
    uv run python -m vetce.pipeline.tag_all --retag-all

Behavior:
- Walks listings where subject_category IS NULL (default), or all listings
  if --retag-all is passed.
- For each listing, calls Claude to classify.
- Persists category, tagged_at, and logs the reason.
- Reports progress every 10 listings.
- Reports total cost and time at the end.
- Resume-safe: re-running picks up where it left off.
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from anthropic import Anthropic, APIError
from sqlalchemy import or_, select, update

from vetce.config import settings
from vetce.db import SessionLocal
from vetce.logging import configure_logging, log
from vetce.models import Listing
from vetce.pipeline.tagger import (
    DENTAL_CATEGORIES,
    NON_DENTAL_SLUG,
    classify_listing,
)


# Pricing constants for Claude Haiku 4.5 (per million tokens).
# Used for cost reporting only — not for billing.
PRICE_INPUT_PER_MTOK = 1.00
PRICE_OUTPUT_PER_MTOK = 5.00


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-tag listings.")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only tag N listings then stop. Useful for testing.",
    )
    parser.add_argument(
        "--retag-all", action="store_true",
        help="Re-tag every listing, including ones already tagged.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be tagged without calling Claude or writing.",
    )
    args = parser.parse_args()

    configure_logging()
    log.info("tagger_batch_start", limit=args.limit, retag_all=args.retag_all)

    session = SessionLocal()
    client = Anthropic(api_key=settings.anthropic_api_key)

    # Select listings to tag.
    stmt = select(Listing).order_by(Listing.id)
    if not args.retag_all:
        stmt = stmt.where(Listing.subject_category.is_(None))
    if args.limit:
        stmt = stmt.limit(args.limit)

    listings = list(session.scalars(stmt).all())
    total = len(listings)

    if total == 0:
        print("Nothing to tag. All listings already have a category.")
        return

    print(f"Tagging {total} listings...")
    if args.dry_run:
        print("(DRY RUN — no API calls, no writes)")

    start_time = time.perf_counter()
    total_input_tokens = 0
    total_output_tokens = 0
    category_counts: dict[str, int] = {}
    errors: list[tuple[int, str]] = []

    for i, listing in enumerate(listings, start=1):
        if args.dry_run:
            print(f"  [{i}/{total}] (dry-run) {listing.title[:80]}")
            continue

        try:
            result = classify_listing(
                listing.title,
                listing.description,
                client=client,
            )
        except APIError as e:
            log.error("tagger_failed", listing_id=listing.id, error=str(e))
            errors.append((listing.id, str(e)))
            continue
        except Exception as e:
            log.error("tagger_unexpected_error", listing_id=listing.id, error=str(e))
            errors.append((listing.id, str(e)))
            continue

        # Persist the result.
        session.execute(
            update(Listing)
            .where(Listing.id == listing.id)
            .values(
                subject_category=result.category,
                subject_tagged_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        # Tally.
        total_input_tokens += result.input_tokens
        total_output_tokens += result.output_tokens
        category_counts[result.category] = category_counts.get(result.category, 0) + 1

        # Progress.
        if i % 10 == 0 or i == total:
            elapsed = time.perf_counter() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  [{i}/{total}] {rate:.1f} listings/sec — latest: '{listing.title[:50]}' -> {result.category}")

    # Final report.
    elapsed = time.perf_counter() - start_time
    cost = (
        (total_input_tokens / 1_000_000) * PRICE_INPUT_PER_MTOK
        + (total_output_tokens / 1_000_000) * PRICE_OUTPUT_PER_MTOK
    )

    print()
    print("=" * 60)
    print(f"Tagged {total - len(errors)}/{total} listings in {elapsed:.1f}s")
    print(f"Tokens used: {total_input_tokens:,} in, {total_output_tokens:,} out")
    print(f"Estimated cost: ${cost:.4f}")
    print()
    print("Category breakdown:")
    for slug, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        display = DENTAL_CATEGORIES.get(slug, slug)
        pct = (count / total) * 100
        marker = " (hidden)" if slug == NON_DENTAL_SLUG else ""
        print(f"  {display:<35} {count:>4} ({pct:>5.1f}%){marker}")

    if errors:
        print()
        print(f"Errors on {len(errors)} listings:")
        for listing_id, err in errors[:5]:
            print(f"  Listing {listing_id}: {err[:100]}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")


if __name__ == "__main__":
    main()