"""The parameter side of the diacritic fold.

`letter_spans` folds the text; until these helpers existed nothing folded the
parameter compared against it, so `vowel="ä"` was unsatisfiable in German and
`deleted="s"` never removed a `ß`. See ADR 0035 and the 2026-09-02 sweep,
Finding 1.
"""

import pytest

from denckring.core.errors import InvalidParams
from denckring.core.text import fold_letter, single_letter
from denckring.lang import get_pack


def test_folding_a_plain_letter_lowercases_it() -> None:
    assert fold_letter("A", get_pack("en"), fold=True) == "a"


def test_folding_an_umlaut_strips_the_mark() -> None:
    assert fold_letter("Ä", get_pack("de"), fold=True) == "a"


def test_not_folding_keeps_the_mark_and_only_lowercases() -> None:
    assert fold_letter("Ä", get_pack("de"), fold=False) == "ä"


def test_eszett_folds_to_two_letters() -> None:
    """`ß` casefolds to `ss`, so one character contributes two letters — the
    fact `slenderizing` and `acrostic` both got wrong."""
    assert fold_letter("ß", get_pack("de"), fold=True) == "ss"


def test_the_french_ligature_folds_to_two_letters() -> None:
    assert fold_letter("œ", get_pack("fr"), fold=True) == "oe"


def test_a_single_letter_parameter_folds_to_one_letter() -> None:
    assert (
        single_letter("ä", get_pack("de"), fold=True, procedure_id="univocalic", field="vowel")
        == "a"
    )


def test_a_single_letter_parameter_is_lowercased_when_not_folding() -> None:
    assert (
        single_letter("Ä", get_pack("de"), fold=False, procedure_id="univocalic", field="vowel")
        == "ä"
    )


def test_a_parameter_folding_to_two_letters_is_refused_by_name() -> None:
    """`degenerate_output` advising `allow_identity` was the old answer, and it
    named the wrong cause entirely — see the spec's D4."""
    with pytest.raises(InvalidParams) as caught:
        single_letter("ß", get_pack("de"), fold=True, procedure_id="slenderizing", field="deleted")
    message = str(caught.value)
    assert "deleted" in message
    assert "ss" in message
    assert "fold_diacritics" in message


def test_the_refusal_names_the_procedure() -> None:
    with pytest.raises(InvalidParams) as caught:
        single_letter("œ", get_pack("fr"), fold=True, procedure_id="univocalic", field="vowel")
    assert caught.value.procedure_id == "univocalic"


def test_a_letter_that_folds_to_two_is_usable_with_folding_off() -> None:
    """The refusal must name a way out that actually works."""
    assert (
        single_letter("ß", get_pack("de"), fold=False, procedure_id="slenderizing", field="deleted")
        == "ß"
    )
