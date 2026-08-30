"""The German syllable heuristic, and the honesty of it.

Mirrors tests/test_syllables.py for English. The German heuristic is simpler
than the English one on purpose — see the docstring on GermanPack.syllable_count
and D2 in docs/superpowers/specs/2026-08-30-german-prosody-design.md.
"""

import pytest

from denckring.lang.base import SYLLABLES_DICTIONARY, SYLLABLES_HEURISTIC
from denckring.lang.de import GermanPack

CORE = GermanPack()


def test_core_german_declares_only_the_heuristic() -> None:
    assert SYLLABLES_HEURISTIC in CORE.capabilities
    assert SYLLABLES_DICTIONARY not in CORE.capabilities


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("Haus", 1),  # au is one nucleus
        ("Deich", 1),  # ei likewise
        ("zwölf", 1),  # folded to zwolf; one vowel run
        ("Katze", 2),  # the case English gets wrong: final -e is pronounced
        ("Blume", 2),
        ("Häuser", 2),  # äu folds to au and stays one nucleus
        ("Straße", 2),  # ß folds to ss; vowels unaffected
        ("Bahnhof", 2),
        ("Boxkämpfer", 3),
    ],
)
def test_the_heuristic_counts_german_syllables(word: str, expected: int) -> None:
    assert CORE.syllable_count(word)[0] == expected


@pytest.mark.parametrize(("word", "counted", "truth"), [("Museum", 2, 3), ("Familie", 3, 4)])
def test_a_vowel_sequence_across_a_morpheme_boundary_undercounts(
    word: str, counted: int, truth: int
) -> None:
    """Pinned as known behaviour, not discovered later as a bug.

    A vowel run is one nucleus, which is right for a diphthong and wrong for a
    sequence spanning a boundary: Museum is Mu-se-um and Familie is Fa-mi-li-e.
    This is exactly what ADR 0012's `exact` flag exists to declare, and it is the
    same class of error the English heuristic already ships with. If a future
    change makes these right, update the numbers — do not delete the test.
    """
    assert CORE.syllable_count(word)[0] == counted
    assert counted < truth


def test_the_heuristic_never_claims_to_be_exact() -> None:
    for word in ("Katze", "Haus", "Museum", "xyzq"):
        _, exact = CORE.syllable_count(word)
        assert exact is False


def test_the_heuristic_never_returns_less_than_one_for_a_word() -> None:
    for word in ("Angst", "Herbst", "Schnee"):
        count, _ = CORE.syllable_count(word)
        assert count >= 1


def test_an_empty_string_has_no_syllables() -> None:
    assert CORE.syllable_count("") == (0, False)
