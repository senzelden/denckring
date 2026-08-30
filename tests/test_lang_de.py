import pytest

from denckring.core.errors import MissingCapability
from denckring.lang import get_pack, installed_languages
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS
from denckring.lang.de import GermanPack


def test_german_pack_is_discovered() -> None:
    assert "de" in installed_languages()
    assert get_pack("de").lang == "de"


def test_german_declares_the_batch_one_capabilities() -> None:
    assert {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES} <= get_pack("de").capabilities


def test_german_has_no_lexicon_or_syllable_segmentation() -> None:
    # The core pack specifically: get_pack("de") resolves to the data pack when
    # denckring[de] is installed, and that one does provide these.
    pack = GermanPack()
    with pytest.raises(MissingCapability):
        pack.syllables("Wetter")
    with pytest.raises(MissingCapability):
        list(pack.nouns())


def test_umlauts_are_vowels() -> None:
    assert {"ä", "ö", "ü"} <= get_pack("de").vowels()


def test_eszett_has_an_ascender() -> None:
    assert get_pack("de").exceeds_x_height("ß")


def test_umlauts_exceed_the_x_height() -> None:
    pack = get_pack("de")
    assert all(pack.exceeds_x_height(ch) for ch in "äöü")


def test_a_bare_vowel_stays_within_the_x_height() -> None:
    assert not get_pack("de").exceeds_x_height("a")


def test_the_alphabet_is_the_twenty_six_base_letters() -> None:
    assert get_pack("de").alphabet() == "abcdefghijklmnopqrstuvwxyz"


def test_folding_expands_eszett_and_strips_umlauts() -> None:
    pack = get_pack("de")
    assert pack.fold_diacritics("ß") == "ss"
    assert pack.fold_diacritics("Ä") == "a"
