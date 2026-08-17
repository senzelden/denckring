import string

import pytest

from denckring import check
from denckring.core.errors import InvalidParams

PANGRAM = "Pack my box with five dozen liquor jugs"  # 32 letters


def test_a_short_pangram_is_satisfied() -> None:
    report = check("pangrammatic_window", PANGRAM, max_length=40)
    assert report.satisfied
    assert report.metrics["letters"] == 32.0


def test_a_pangram_over_the_bar_violates() -> None:
    report = check("pangrammatic_window", PANGRAM, max_length=30)
    assert not report.satisfied
    assert any(v.rule == "window_too_long" for v in report.violations)


def test_a_missing_letter_violates() -> None:
    report = check("pangrammatic_window", "the quick brown fox", max_length=100)
    assert not report.satisfied
    assert any(v.rule == "missing_letter" for v in report.violations)


def test_an_empty_text_is_unsatisfied_not_vacuous() -> None:
    """Like pangram: it requires something rather than forbidding something, so
    an empty text supplies none of it."""
    report = check("pangrammatic_window", "", max_length=100)
    assert not report.satisfied
    assert report.score == 0.0
    assert report.violations


def test_exactly_at_the_bar_is_satisfied() -> None:
    assert check("pangrammatic_window", PANGRAM, max_length=32).satisfied


def test_max_length_is_required() -> None:
    with pytest.raises(InvalidParams):
        check("pangrammatic_window", PANGRAM)


def test_max_length_below_the_alphabet_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("pangrammatic_window", PANGRAM, max_length=25)


def test_both_rules_can_violate_at_once() -> None:
    """Missing letters and an overlong window are independent faults; a text
    can fail both, and the report must stay coherent about it."""
    report = check("pangrammatic_window", "the quick brown fox " * 3, max_length=26)
    assert not report.satisfied
    rules = {v.rule for v in report.violations}
    assert "missing_letter" in rules
    assert "window_too_long" in rules
    assert report.score < 1.0


def test_satisfied_implies_perfect_score() -> None:
    report = check("pangrammatic_window", PANGRAM, max_length=40)
    assert report.satisfied is (report.score == 1.0)


def test_padding_with_spaces_does_not_count_toward_the_window() -> None:
    """`window_too_long` compares the letter count, not len(text): 26 letters
    padded with 40 spaces is not too long, even though len(text) is 66."""

    text = string.ascii_lowercase + " " * 40
    report = check("pangrammatic_window", text, max_length=26)
    assert report.satisfied
    assert report.metrics["letters"] == 26.0
    assert len(text) == 66
