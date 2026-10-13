import unicodedata

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


# ADR 0064: `capitals_only`, the reading Hilton calls a pretext, opt-in.

ELIZABETH = "My Day Is Closed In Immortality."


def test_capitals_only_off_counts_every_numeral_as_before() -> None:
    """The default is Hilton's: the superfluous lower-case numerals count too."""
    assert check("chronogram", ELIZABETH, year=1603).metrics["total"] == 4204
    assert check("chronogram", ELIZABETH, year=1603, capitals_only=False) == check(
        "chronogram", ELIZABETH, year=1603
    )


def test_capitals_only_counts_only_capital_numerals() -> None:
    report = check("chronogram", ELIZABETH, year=1603, capitals_only=True)
    assert report.satisfied
    assert report.metrics == {"total": 1603.0, "numerals": 6.0}


def test_lowercase_numerals_are_ignored_under_capitals_only() -> None:
    assert check("chronogram", "Mild vixen", year=1567).satisfied
    report = check("chronogram", "Mild vixen", year=1567, capitals_only=True)
    assert [v.rule for v in report.violations] == ["wrong_total"]
    assert report.metrics == {"total": 1000.0, "numerals": 1.0}


def test_an_accented_capital_counts_only_when_folded() -> None:
    """Case is read from the caller's text, folding from the parameter: `Ï` is a
    capital, and it is an I only when diacritics fold."""
    folded = check("chronogram", "Ïx", year=1, capitals_only=True)
    assert folded.metrics == {"total": 1.0, "numerals": 1.0}
    kept = check("chronogram", "Ïx", year=1, capitals_only=True, fold_diacritics=False)
    assert kept.metrics == {"total": 0.0, "numerals": 0.0}


def test_a_lowercase_accented_numeral_does_not_count_under_capitals_only() -> None:
    assert check("chronogram", "ïX", year=10, capitals_only=True).metrics["total"] == 10


def test_a_decomposed_capital_counts_as_its_composed_form() -> None:
    nfd = unicodedata.normalize("NFD", "Ïx")
    assert len(nfd) == 3
    assert check("chronogram", nfd, year=1, capitals_only=True).metrics["total"] == 1


def test_german_letters_are_never_numerals() -> None:
    """ä ö ü ß fold to a o u ss, none of them a numeral, so they add nothing either way."""
    for fold in (True, False):
        for capitals_only in (True, False):
            report = check(
                "chronogram",
                "ÄÖÜẞ äöüß",
                year=0,
                fold_diacritics=fold,
                capitals_only=capitals_only,
            )
            assert report.metrics == {"total": 0.0, "numerals": 0.0}
