import pytest

from denckring import check

pytest.importorskip("denckring_en_data")


def test_a_word_reversing_into_another_word_is_satisfied() -> None:
    assert check("semordnilap", "stressed").satisfied


def test_a_palindrome_is_not_a_semordnilap() -> None:
    report = check("semordnilap", "level")
    assert not report.satisfied
    assert report.violations[0].rule == "palindrome_not_semordnilap"


def test_a_reversal_that_is_not_a_word_is_a_violation() -> None:
    # Not "cat": the membership oracle includes CMUdict, which lists "tac".
    report = check("semordnilap", "table")
    assert report.violations[0].rule == "reversal_is_not_a_word"
