import pytest

from denckring.core.errors import MissingCapability
from denckring.lang import get_pack, installed_languages
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS
from denckring.lang.fr import FrenchPack
from denckring.procedures.anagram import Anagram
from denckring.procedures.haiku import Haiku


def test_french_pack_is_discovered() -> None:
    assert "fr" in installed_languages()
    assert get_pack("fr").lang == "fr"


def test_french_declares_the_same_four_capabilities_as_german() -> None:
    assert {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES} <= get_pack("fr").capabilities


def test_french_has_no_lexicon_or_syllables() -> None:
    pack = FrenchPack()
    with pytest.raises(MissingCapability):
        pack.syllables("chien")
    with pytest.raises(MissingCapability):
        list(pack.nouns())


def test_the_alphabet_is_the_twenty_six_base_letters() -> None:
    assert get_pack("fr").alphabet() == "abcdefghijklmnopqrstuvwxyz"


def test_y_is_a_vowel() -> None:
    assert "y" in get_pack("fr").vowels()


def test_a_core_only_check_runs_in_french() -> None:
    """The reported oddity: French anagram pairs validate perfectly under the
    tokeniser and the letter multiset, neither of which is French-specific, yet
    `lang="fr"` raised `UnknownLanguage` before there was a French pack."""
    report = Anagram().check("chien", lang="fr", source="niche")
    assert report.satisfied


def test_a_row_needing_a_lexicon_fails_on_the_capability_not_the_language() -> None:
    """`n_plus_7` was this test's original subject: it named `lexicon.nouns`,
    which `denckring[fr]` now supplies (chapter 6), so it runs in French and can
    no longer illustrate the failure. `haiku` needs `syllables.heuristic`, which
    this chapter deliberately ships no data for — the error must still name the
    missing capability rather than the language, which is merely undersupplied.
    """
    with pytest.raises(MissingCapability) as excinfo:
        Haiku().check("un vieil étang", lang="fr")
    assert "syllables.heuristic" in str(excinfo.value)


def test_the_ligatures_fold_because_nfkd_does_not_fold_them() -> None:
    """`ß` folds to `ss` for free because `casefold()` maps it. `œ` and `æ` have
    no such mapping and no NFKD decomposition, so the base fold leaves them
    whole — which would count `œ` as one letter no anagram could match."""
    pack = FrenchPack()
    assert pack.fold_diacritics("œ") == "oe"
    assert pack.fold_diacritics("æ") == "ae"
    assert pack.fold_diacritics("é") == "e"
