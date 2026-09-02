"""One cause, several rows: a parameter compared against folded text.

`fold_diacritics` defaults to true, the text side folds, and the parameter side
did not — so an accented parameter was unsatisfiable and the violation mixed a
folded `found` with an unfolded `expected`. ADR 0035, and the 2026-09-02 MCP
sweep, Finding 1.
"""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_a_german_umlaut_vowel_is_satisfiable() -> None:
    """`vowel="ä"` reported found "a" against expected "ä" — the seam exactly."""
    assert check("univocalic", "Bäh", lang="de", vowel="ä").satisfied


def test_the_umlaut_vowel_still_rejects_a_foreign_vowel() -> None:
    report = check("univocalic", "Bähe", lang="de", vowel="ä")
    assert not report.satisfied
    assert [v.found for v in report.violations] == ["e"]


def test_an_unfolded_umlaut_vowel_is_distinct_from_its_base() -> None:
    """With folding off, `ä` and `a` are different letters and must stay so."""
    assert not check("univocalic", "Bah", lang="de", vowel="ä", fold_diacritics=False).satisfied
    assert check("univocalic", "Bäh", lang="de", vowel="ä", fold_diacritics=False).satisfied


def test_two_umlaut_vowels_are_satisfiable() -> None:
    assert check("bivocalic", "Bähö", lang="de", vowels="äö").satisfied


def test_an_eszett_consonant_is_refused_by_name() -> None:
    """`consonant="ß"` was unsatisfiable and reported a two-letter `expected`
    against a one-character `got`. D4 refuses it and names the way out."""
    with pytest.raises(InvalidParams) as caught:
        check("monoconsonantal", "Straße", lang="de", consonant="ß")
    assert "fold_diacritics" in str(caught.value)


def test_an_eszett_consonant_works_with_folding_off() -> None:
    assert check(
        "monoconsonantal", "ßeiß", lang="de", consonant="ß", fold_diacritics=False
    ).satisfied


def test_english_is_unchanged_by_the_parameter_fold() -> None:
    """The seam is invisible in ASCII, which is why English never saw it."""
    assert check("univocalic", "Persever, ye perfect men", lang="en", vowel="e").satisfied
    assert check("monoconsonantal", "nine no one", lang="en", consonant="n").satisfied


def test_an_eszett_in_an_acrostic_target_claims_two_units() -> None:
    """`expected` was a two-character "ss" compared against a one-character
    `got` — a "letter" that no unit could ever match. Flattened, ß claims the
    two units its two letters need. ADR 0035, D3.
    """
    assert check("acrostic", "Sonne\nsehr\ntanzt", lang="de", target="ßt", unit="line").satisfied


def test_the_flattened_target_still_reports_a_wrong_letter() -> None:
    report = check("acrostic", "Sonne\nmehr\ntanzt", lang="de", target="ßt", unit="line")
    assert not report.satisfied
    assert [(v.rule, v.found, v.expected) for v in report.violations] == [
        ("wrong_letter", "m", "s")
    ]


def test_telestich_inherits_the_flattened_target() -> None:
    """`telestich` subclasses `Acrostic` and reads the last letter of each unit."""
    assert check("telestich", "das\nes\nvot", lang="de", target="ßt", unit="line").satisfied


def test_a_double_acrostic_target_flattens_on_both_edges() -> None:
    assert check(
        "double_acrostic",
        "sonnes\nsehrs\ntanzt",
        lang="de",
        first="ßt",
        last="sst",
    ).satisfied
