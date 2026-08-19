"""Four rows asked for the wrong thing.

Measuring what WordNet can do showed that `lexicon.synonyms` has no honest
consumer: one row needs a parameter, one needs part-of-speech tagging, and one
cannot be satisfied by ordinary text at all.
"""

import pytest

from denckring.core import catalogue


def test_kangaroo_word_needs_the_word_list_not_a_thesaurus() -> None:
    """Whether two words are synonyms is the writer's claim; that they are words
    and that the letters appear in order is what a program can check."""
    requires = catalogue.get("kangaroo_word").requires
    assert "lexicon.words" in requires
    assert "lexicon.synonyms" not in requires


def test_chimera_substitutes_by_part_of_speech_not_by_meaning() -> None:
    requires = catalogue.get("chimera").requires
    assert "pos" in requires
    assert "lexicon.synonyms" not in requires


def test_definitional_translation_needs_glosses_in_the_target_language() -> None:
    requires = catalogue.get("definitional_translation").requires
    assert "lexicon.glosses.bilingual" in requires


@pytest.mark.parametrize(
    "row", ["synonymic_substitution", "antonymic_substitution", "antonymic_translation"]
)
def test_the_unsatisfiable_rows_record_why_they_wait(row: str) -> None:
    """Blocked for a stated reason beats blocked for an unbuilt one."""
    assert catalogue.get(row).notes
