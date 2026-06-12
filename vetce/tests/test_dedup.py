"""Unit tests for vetce.pipeline.dedup pure functions.

These functions have no DB or HTTP dependencies, so tests are fast
and deterministic.
"""
from __future__ import annotations

import pytest

from vetce.pipeline.dedup import jaccard_similarity, normalize_title


# ============================================================
# normalize_title
# ============================================================

class TestNormalizeTitle:
    def test_lowercases(self) -> None:
        assert normalize_title("MODULE 1") == "module 1"

    def test_strips_punctuation(self) -> None:
        assert normalize_title("Module 1: Focus on Dermatology") == "module 1 focus on dermatology"

    def test_normalizes_em_dashes(self) -> None:
        assert normalize_title("MODULE 1 — FOCUS ON DERMATOLOGY") == "module 1 focus on dermatology"

    def test_normalizes_en_dashes(self) -> None:
        assert normalize_title("Module 1 – Focus") == "module 1 focus"

    def test_collapses_multiple_whitespace(self) -> None:
        assert normalize_title("  Canine   Atopic   Dermatitis  ") == "canine atopic dermatitis"

    def test_em_and_colon_produce_same_output(self) -> None:
        """The whole point of normalization: 'MODULE 1 — FOCUS' and
        'Module 1: Focus' should normalize identically."""
        assert (
            normalize_title("MODULE 1 — FOCUS ON DERMATOLOGY")
            == normalize_title("Module 1: Focus on Dermatology")
        )

    def test_preserves_numbers(self) -> None:
        """Module 1 and Module 2 must stay distinct."""
        assert normalize_title("Module 1") != normalize_title("Module 2")

    def test_handles_none(self) -> None:
        assert normalize_title(None) == ""

    def test_handles_empty_string(self) -> None:
        assert normalize_title("") == ""

    def test_handles_apostrophes(self) -> None:
        # Apostrophes are punctuation; they should be stripped.
        assert normalize_title("That Darn Cat! If It's Vomiting") == "that darn cat if its vomiting"


# ============================================================
# jaccard_similarity
# ============================================================

class TestJaccardSimilarity:
    def test_identical_strings_score_one(self) -> None:
        assert jaccard_similarity("module 1 dermatology", "module 1 dermatology") == 1.0

    def test_completely_disjoint_strings_score_zero(self) -> None:
        assert jaccard_similarity("cats", "dogs") == 0.0

    def test_one_word_difference(self) -> None:
        # {module, 1, dermatology} vs {module, 2, dermatology}
        # Intersection = {module, dermatology} (size 2)
        # Union = {module, 1, 2, dermatology} (size 4)
        # Jaccard = 2/4 = 0.5
        assert jaccard_similarity("module 1 dermatology", "module 2 dermatology") == 0.5

    def test_empty_string_first_arg(self) -> None:
        assert jaccard_similarity("", "anything goes here") == 0.0

    def test_empty_string_second_arg(self) -> None:
        assert jaccard_similarity("anything goes here", "") == 0.0

    def test_realistic_case_added_word_clears_85_threshold(self) -> None:
        """Real-world case from Layer 2 testing: adding one word to a
        7-word title gives 7/8 = 0.875, above 0.85, below 0.90."""
        a = "maxillofacial trauma and fundamentals in oral surgery"
        b = "maxillofacial trauma and fundamentals in oral surgery workshop"
        score = jaccard_similarity(a, b)
        assert 0.87 < score < 0.88

    def test_subset_relationship(self) -> None:
        # {a, b, c} vs {a, b, c, d}
        # Intersection = 3, Union = 4
        assert jaccard_similarity("a b c", "a b c d") == 0.75

    def test_word_order_does_not_matter(self) -> None:
        assert jaccard_similarity("cat dog bird", "bird dog cat") == 1.0

    def test_duplicate_words_dont_inflate_score(self) -> None:
        # Sets deduplicate naturally.
        assert jaccard_similarity("cat cat cat", "cat") == 1.0