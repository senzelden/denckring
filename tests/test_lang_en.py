import pytest

from denckring.core.errors import MissingCapability, UnknownLanguage
from denckring.lang import get_pack
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS


def test_english_pack_declares_the_batch_one_capabilities() -> None:
    pack = get_pack("en")
    assert {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES} <= pack.capabilities


def test_unknown_language_raises_with_install_hint() -> None:
    # French has no pack yet; German does, and is covered in test_lang_de.
    with pytest.raises(UnknownLanguage, match=r"denckring\[fr\]"):
        get_pack("fr")


def test_undeclared_capability_raises_rather_than_approximating() -> None:
    pack = get_pack("en")
    with pytest.raises(MissingCapability):
        pack.syllables("potato")
    with pytest.raises(MissingCapability):
        list(pack.nouns())


def test_tokenize_keeps_internal_apostrophes_and_drops_punctuation() -> None:
    assert get_pack("en").tokenize("Don't stop, Anna!") == ["Don't", "stop", "Anna"]


def test_fold_diacritics_maps_accented_letters_to_bare_ones() -> None:
    pack = get_pack("en")
    assert pack.fold_diacritics("é") == "e"
    assert pack.fold_diacritics("E") == "e"
    assert pack.fold_diacritics("ß") == "ss"


def test_letter_shapes_cover_the_prisoner_constraint_set() -> None:
    pack = get_pack("en")
    assert pack.ascenders() | pack.descenders() == set("bdfghjklpqty")
