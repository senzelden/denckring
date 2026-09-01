"""Lexique's SAMPA against hand-checked words.

`@` is the nasal /ɑ̃/ and `2` is /ø/ (and, after a bare orthographic -e, the
schwa). Getting those two wrong is worth fifteen points of line accuracy and
shows up as a plausible peak one syllable short, so they are pinned here.
"""

import pytest
from denckring_fr_data.sampa import IPA_VOWELS, to_ipa, to_phonemes


@pytest.mark.parametrize(
    ("sampa", "ipa"),
    [
        ("d@", "dɑ̃"),  # dans - @ is the nasal, not a schwa
        ("@", "ɑ̃"),  # en
        ("dyR@", "dyʁɑ̃"),  # durant
        ("d2", "dø"),  # de AND deux: Lexique spells both this way
        ("le", "le"),  # les - no schwa at all
        ("bEl", "bɛl"),  # belle
        ("fam", "fam"),  # femme
        ("Zwa", "ʒwa"),  # joie
        ("kaR@t", "kaʁɑ̃t"),  # quarante
        ("pRet@sj§", "pʁetɑ̃sjɔ̃"),  # prétentions
        ("f8ij@", "fɥijɑ̃"),  # fuyant
        ("bEtiG", "bɛtiŋ"),  # betting - G is the velar nasal, not /ɡ/
        ("ak§paNa", "akɔ̃paɲa"),  # accompagna - N is the palatal nasal
    ],
)
def test_sampa_converts_to_ipa(sampa: str, ipa: str) -> None:
    assert to_ipa(sampa) == ipa


def test_phonemes_split_one_symbol_at_a_time() -> None:
    """The nasal is one phoneme, not a vowel plus a combining tilde."""
    assert to_phonemes("d@") == ["d", "ɑ̃"]


def test_the_nasal_is_a_vowel_and_the_glides_are_not() -> None:
    """A glide carries no syllable of its own, which is the test
    `is_vowel_phoneme` exists to answer (ADR 0030)."""
    assert "ɑ̃" in IPA_VOWELS
    assert "ø" in IPA_VOWELS
    assert "j" not in IPA_VOWELS
    assert "w" not in IPA_VOWELS
    assert "ɥ" not in IPA_VOWELS


def test_an_unmapped_symbol_raises_rather_than_passing_through() -> None:
    """A silent pass-through is how a transcription scheme leaks into a count."""
    with pytest.raises(KeyError):
        to_ipa("d¤")


def test_every_symbol_lexique_uses_has_a_mapping() -> None:
    """Whole-branch review Finding 7: the old test of this name swept no
    symbol -- it only asserted that one invented, never-shipped character
    raises. Sweep every distinct character that appears anywhere in the
    125,653-row `phon` column and assert each is in `SAMPA_TO_IPA`, which is
    what the name has always promised. Measured over the shipped table on
    2026-09-01: zero unmapped symbols. If this ever fails, it is a real
    defect -- a table update or a new Lexique release added a symbol this
    project has not looked at -- and must not be weakened to pass."""
    from denckring_fr_data import syllable_table
    from denckring_fr_data.sampa import SAMPA_TO_IPA

    symbols: set[str] = set()
    for _nbsyll, phon, _orthosyll in syllable_table().values():
        symbols.update(phon)
    unmapped = symbols - SAMPA_TO_IPA.keys()
    assert not unmapped, f"unmapped SAMPA symbols: {sorted(unmapped)}"
