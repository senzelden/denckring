"""The catalogue is a published dataset. A row that misstates what a procedure
needs is a defect in it, and these are the seven this batch corrects.
"""

import pytest

from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure

UNDERSTATED = {
    "word_ladder": "lexicon.words",
    "tmesis": "lexicon.words",
    "spoonerism": "phonemes",
}

BLOCKED = {
    "homosyntaxism": "pos",
    "verbless_prose": "pos",
    "homophonic_translation": "phonemes.bilingual",
    "perverb": "corpus.proverbs",
}

UNDECIDABLE = ["back_translation", "transduction", "intralingual_translation"]


#: pytest's own "pid" spelling, not "procedure_id" — the shared conftest's
#: `pytest_generate_tests` auto-parametrizes any test whose fixturenames
#: include the literal name `procedure_id` across every *registered*
#: procedure, which collides with an explicit `@pytest.mark.parametrize` of
#: the same name and would raise `duplicate parametrization of 'procedure_id'`
#: at collection time. These rows are not all registered anyway.
@pytest.mark.parametrize("pid,capability", sorted(UNDERSTATED.items()))
def test_understated_requires_are_corrected(pid: str, capability: str) -> None:
    assert capability in catalogue.get(pid).requires


@pytest.mark.parametrize("pid,capability", sorted(BLOCKED.items()))
def test_blocked_rows_name_what_they_need(pid: str, capability: str) -> None:
    """A row blocked on a capability nothing provides must still say which one."""
    assert capability in catalogue.get(pid).requires


@pytest.mark.parametrize("pid", UNDECIDABLE)
def test_undecidable_rows_are_reclassified(pid: str) -> None:
    meta = catalogue.get(pid)
    assert meta.checkability == "none"
    assert meta.notes, f"{pid} must record why no criterion exists"


def test_the_generic_composite_row_is_renamed() -> None:
    """Its definition describes any composite constraint, not one named pair."""
    with pytest.raises(UnknownProcedure):
        catalogue.get("univocalic_lipogram_pair")
    assert catalogue.get("multiple_constraint")


def test_haikuizations_phonemes_correction_is_reversed() -> None:
    """R18: an earlier correction added `phonemes` to `haikuization` on the
    assumption a rhyme-word reading could be told apart from a line-end one.
    It cannot, in this codebase — `rhyme_keys` always resolves a line to its
    final word regardless of whether it pronounces as a rhyme with anything,
    so requiring `phonemes` bought fragility on an out-of-dictionary line
    ending and no corresponding check. The row runs on `tokens` alone, and
    the reversal is recorded in its own `notes`."""
    meta = catalogue.get("haikuization")
    assert "phonemes" not in meta.requires
    assert meta.notes
