import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_numerals_summing_to_the_year_are_satisfied() -> None:
    assert check("chronogram", "LVX", year=65).satisfied


def test_a_wrong_total_is_a_violation() -> None:
    report = check("chronogram", "LVX", year=100)
    assert not report.satisfied
    assert report.violations[0].found == "65"


def test_score_rises_as_the_total_approaches_the_year() -> None:
    near = check("chronogram", "LVX", year=70).score
    far = check("chronogram", "LVX", year=1000).score
    assert near > far


def test_text_without_numerals_scores_zero() -> None:
    assert check("chronogram", "ashen", year=50).score == 0.0


def test_a_bare_numeral_passes_unless_a_minimum_length_is_asked_for() -> None:
    """A9: `MMXXVI` passed for 2026 though the row asks for a phrase."""
    assert check("chronogram", "MMXXVI", year=2026).satisfied
    report = check("chronogram", "MMXXVI", year=2026, min_letters=12)
    assert not report.satisfied
    assert 0.0 < report.score < 1.0
    assert [v.rule for v in report.violations] == ["too_short"]
    assert report.violations[0].found == "6 letters"


def test_a_long_enough_phrase_meets_the_minimum() -> None:
    assert check("chronogram", "a bright sun", year=1, min_letters=10).satisfied


def test_a_short_wrong_total_reports_both() -> None:
    report = check("chronogram", "LVX", year=100, min_letters=10)
    assert [v.rule for v in report.violations] == ["wrong_total", "too_short"]
    assert report.score <= check("chronogram", "LVX", year=100).score


def test_a_negative_minimum_is_refused() -> None:
    with pytest.raises(InvalidParams, match="greater than or equal to 0"):
        check("chronogram", "LVX", year=65, min_letters=-1)
