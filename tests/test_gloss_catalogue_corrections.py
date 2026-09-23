"""Different rows ask different lexical questions.

ADR 0049 gives strict substitution a dictionary-membership contract and makes
bilingual gloss data an explicit input. Neither changes kangaroo-word's caller
claim or chimera's part-of-speech reading.
"""

import pytest

from denckring import check
from denckring.core import catalogue, registry
from denckring.core.errors import InvalidParams


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
    assert "lexicon.glosses.bilingual" not in requires
    model = registry.get("definitional_translation").params_model()
    assert model.model_fields["data"].is_required()
    with pytest.raises(InvalidParams):
        check("definitional_translation", "animal", source="cat")


@pytest.mark.parametrize(
    "row", ["synonymic_substitution", "antonymic_substitution", "antonymic_translation"]
)
def test_the_strict_rows_are_built_and_record_their_limits(row: str) -> None:
    """Registration now certifies the bounded interpretation in ADR 0049."""
    assert row in registry.all_procedures()
    assert catalogue.get(row).notes
