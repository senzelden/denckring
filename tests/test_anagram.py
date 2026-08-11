import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_a_true_anagram_is_satisfied() -> None:
    assert check("anagram", "silent", source="listen").satisfied


def test_a_different_letter_multiset_is_not_satisfied() -> None:
    assert not check("anagram", "silence", source="listen").satisfied


def test_spacing_and_case_are_ignored() -> None:
    assert check("anagram", "Enlist!", source="listen").satisfied


def test_surplus_and_missing_letters_are_both_reported() -> None:
    report = check("anagram", "listenx", source="listen")
    assert {v.rule for v in report.violations} == {"surplus_letter"}


def test_missing_source_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("anagram", "silent")
