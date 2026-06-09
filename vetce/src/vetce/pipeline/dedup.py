"""Title normalization and fuzzy similarity for deduplication.

normalize_title() produces a canonical string for comparison purposes:
  - lowercase
  - dashes/slashes → spaces
  - punctuation stripped
  - whitespace collapsed

jaccard_similarity() scores two normalized titles by token overlap.

Both functions are pure (no DB, no I/O). Easy to unit-test.
"""
from __future__ import annotations

import re

# Match any character that is NOT a letter, digit, or whitespace.
# We strip these (replace with empty string).
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)

# Dashes and slashes get replaced with a space BEFORE punctuation stripping,
# so "module 1—focus" becomes "module 1 focus", not "module 1focus".
_DASH_SLASH_RE = re.compile(r"[-–—/\\]")

# Collapse runs of whitespace to a single space.
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str | None) -> str:
    """Produce a canonical form of a title for comparison.

    Returns "" for None or empty input.

    Examples:
        "MODULE 1 — FOCUS ON DERMATOLOGY" → "module 1 focus on dermatology"
        "Module 1: Focus on Dermatology"  → "module 1 focus on dermatology"
        "  Canine  Atopic  Dermatitis  "  → "canine atopic dermatitis"
    """
    if not title:
        return ""

    s = title.lower()
    s = _DASH_SLASH_RE.sub(" ", s)
    s = _PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity over the word tokens of two strings.

    Both inputs should already be normalized via normalize_title().

    Returns 0.0 if either is empty. Returns 1.0 if both have identical
    token sets (regardless of order or repetition).

    Examples:
        "module 1 focus on dermatology" vs same    → 1.00
        "module 1 dermatology" vs "module 2 dermatology" → 0.50
        "" vs "anything"                            → 0.00
    """
    if not a or not b:
        return 0.0

    tokens_a = set(a.split())
    tokens_b = set(b.split())

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)