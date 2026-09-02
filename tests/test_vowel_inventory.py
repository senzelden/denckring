"""The inventory reading of `vowels()`, split out.

`pack.vowels()` answered three questions at once. `supervocalic` wants the base
letters to require one of each; `monoconsonantal` wants which letters in a text
are vowels; `word_ladder` wants the character set to widen an alphabet with.
English was correct only because its three readings coincide. ADR 0035, D1.
"""

from denckring import check
from denckring.lang import get_pack


def test_every_pack_names_the_same_five() -> None:
    """The definition published for `supervocalic` says five, in every language."""
    for lang in ("en", "de", "fr"):
        assert get_pack(lang).vowel_inventory() == frozenset("aeiou")


def test_the_default_folds_before_removing_the_ambiguous_letters() -> None:
    """Measured: removing `y` without folding first answers eight for German and
    nineteen for French. The order is the whole of the default.
    """
    assert len(get_pack("de").vowels()) == 8
    assert len(get_pack("fr").vowels()) == 21
    assert len(get_pack("de").vowel_inventory()) == 5
    assert len(get_pack("fr").vowel_inventory()) == 5


def test_a_german_supervocalic_is_satisfiable() -> None:
    """No German text could satisfy this row: folded text can never contain
    `ä ö ü`, so they were permanently missing while inflating `a o u` into
    repeated. Here `ä` supplies the `a` and `ß` folds to two consonants."""
    assert check("supervocalic", "Rätsel bloß im Duft", lang="de").satisfied


def test_a_german_supervocalic_still_fails_on_a_repeat() -> None:
    report = check("supervocalic", "Faust bewegt hier Idole.", lang="de")
    assert not report.satisfied
    assert {v.found for v in report.violations if v.rule == "repeated_vowel"} == {"e", "i"}
    assert not [v for v in report.violations if v.rule == "missing_vowel"]


def test_french_does_not_require_y() -> None:
    """French `vowels()` has 21 members including `à â ä ÿ`, so the row demanded
    each of them exactly once in text that had folded them all away. `y` is a
    French vowel letter but the published definition says five."""
    assert check("supervocalic", "Le mot du jardin", lang="fr").satisfied


def test_french_permits_y_without_requiring_it() -> None:
    assert check("supervocalic", "Le stylo du jardin", lang="fr").satisfied


def test_english_is_unchanged() -> None:
    assert check("supervocalic", "facetious", lang="en").satisfied
