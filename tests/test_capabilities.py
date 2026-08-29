"""`lexicon.graded_words`: a capability a flat word list cannot honestly declare."""

import pytest

from denckring.core.errors import MissingCapability
from denckring.lang.base import GRADED_WORDS, WORDS
from denckring.lang.de import GermanPack

en_data = pytest.importorskip("denckring_en_data", reason="needs denckring[en]")
de_data = pytest.importorskip("denckring_de_data", reason="needs denckring[de]")

EnglishDataPack = en_data.EnglishDataPack
GermanDataPack = de_data.GermanDataPack


def test_a_pack_without_the_capability_refuses_rather_than_approximating() -> None:
    """ADR 0004's rule. German's Wikidata list is flat, so it cannot answer this
    question and must not pretend to — a flat list would rank every cover equally
    and the search would be back where it started."""
    with pytest.raises(MissingCapability):
        GermanPack().graded_words()


def test_graded_words_is_a_separate_capability_from_words() -> None:
    """ADR 0015: one capability per question the lexicon is asked. "Is this a
    word" and "give me the words, with how common each is" are different
    questions, and a pack can honestly answer the first and not the second."""
    assert GRADED_WORDS != WORDS
    assert GRADED_WORDS in EnglishDataPack.capabilities
    assert GRADED_WORDS not in GermanDataPack.capabilities
