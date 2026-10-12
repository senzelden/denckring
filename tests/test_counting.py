"""Each claim `reading.counting` makes is what the checker does (ADR 0061 D4)."""

from __future__ import annotations

from typing import Any

import denckring

COUNTING = denckring.describe("chronogram").reading.counting


def total(text: str, **params: Any) -> float:
    return denckring.check("chronogram", text, year=1, **params).metrics["total"]


def test_chronogram_declares_counting() -> None:
    assert COUNTING is not None and COUNTING.combine == "sum"


def test_values_are_the_checker_values() -> None:
    assert COUNTING is not None
    for letter, value in COUNTING.values.items():
        assert total(letter) == value


def test_subtractive_claim_matches() -> None:
    assert COUNTING is not None
    assert (total("IV") == 4) is COUNTING.subtractive


def test_every_occurrence_claim_matches() -> None:
    assert COUNTING is not None
    assert (total("My Day Closed Is In Immortality") == 4204) is COUNTING.every_occurrence


def test_case_claim_matches() -> None:
    assert COUNTING is not None
    assert (total("Ix") != total("IX")) is COUNTING.case_sensitive


def test_digits_and_punctuation_add_nothing() -> None:
    assert total("X 1999, !") == total("X")


def test_folding_is_the_named_parameter() -> None:
    assert COUNTING is not None and COUNTING.folds == "fold_diacritics"
    assert total("ï") == 1 and total("ï", fold_diacritics=False) == 0


def test_rows_that_count_nothing_say_so() -> None:
    assert denckring.describe("lipogram").reading.counting is None
