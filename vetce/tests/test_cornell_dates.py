"""Unit tests for Cornell scraper's date parsing.

The Cornell CVM page presents dates in several formats — single day,
same-month range, cross-month, cross-year. We test each shape directly
since this is one of the most regression-prone helpers in the codebase.
"""
from __future__ import annotations

from datetime import date

import pytest

from vetce.scrapers.sites.cornell_cvm import _parse_dates


class TestParseDates:
    def test_single_day(self) -> None:
        assert _parse_dates("May 16, 2026") == (date(2026, 5, 16), date(2026, 5, 16))

    def test_same_month_range_hyphen(self) -> None:
        assert _parse_dates("May 16-17, 2026") == (date(2026, 5, 16), date(2026, 5, 17))

    def test_same_month_range_en_dash(self) -> None:
        # Normalized to hyphen internally.
        assert _parse_dates("May 16–17, 2026") == (date(2026, 5, 16), date(2026, 5, 17))

    def test_same_month_range_with_spaces(self) -> None:
        assert _parse_dates("May 16 - 17, 2026") == (date(2026, 5, 16), date(2026, 5, 17))

    def test_cross_month_same_year(self) -> None:
        assert _parse_dates("July 26 - August 2, 2026") == (
            date(2026, 7, 26),
            date(2026, 8, 2),
        )

    def test_cross_year(self) -> None:
        # When the year on the left is missing, it inherits from the right.
        assert _parse_dates("December 30, 2026 - January 2, 2027") == (
            date(2026, 12, 30),
            date(2027, 1, 2),
        )

    def test_unparseable_returns_none(self) -> None:
        assert _parse_dates("TBD") == (None, None)

    def test_empty_string_returns_none(self) -> None:
        assert _parse_dates("") == (None, None)

    def test_abbreviated_month(self) -> None:
        # _MONTHS dict supports abbreviations
        assert _parse_dates("May 16, 2026") == _parse_dates("May 16, 2026")
        # Verify abbreviation works
        assert _parse_dates("Oct 9, 2026") == (date(2026, 10, 9), date(2026, 10, 9))