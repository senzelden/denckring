"""The catalogue is a published dataset. A row that misstates what a procedure
needs is a defect in it, and these are the seven this batch corrects.
"""

import pytest

from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure

UNDERSTATED = {
    "word_ladder": "lexicon.words",
    "tmesis": "lexicon.words",
    "haikuization": "phonemes",
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
