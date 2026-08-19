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


def _search(term: str) -> list[str]:
    """What `denckring search` would match — id, every name, every alias."""
    needle = term.casefold()
    return [
        pid
        for pid in catalogue.ids()
        if any(
            needle in field.casefold()
            for field in [pid, *catalogue.get(pid).names.values(), *catalogue.get(pid).aliases]
        )
    ]


def test_the_renamed_row_is_still_findable_by_what_it_used_to_be_called() -> None:
    """Renaming a published row without keeping its old handles findable deletes it
    from the record. `registry.get` resolves ids only and never consults aliases, so
    "kept as an alias" buys nothing unless the alias is the string a reader would
    actually type — the old *id*, and the old published English name, "Compound
    constraint", which the rename dropped entirely.
    """
    for term in ("univocalic_lipogram_pair", "univocalic lipogram pair", "Compound constraint"):
        assert _search(term) == ["multiple_constraint"], f"{term!r} finds nothing"


def test_the_renamed_rows_id_still_suggests_the_row_it_became() -> None:
    """Asking for the old id by id must name the row that replaced it, not just fail."""
    with pytest.raises(UnknownProcedure) as exc_info:
        catalogue.get("univocalic_lipogram_pair")
    assert "multiple_constraint" in exc_info.value.suggestions


def test_the_renamed_rows_aliases_are_its_old_handles_and_not_its_own_name() -> None:
    """`search` already matches names, so "multiple constraint" as an alias of
    *Multiple constraint* bought nothing while displacing the two strings that would
    have. (`n_plus_7` also aliases its own name, `N+7`; that one is a harmless
    duplicate of a symbol its three names already carry, and is left alone.)
    """
    meta = catalogue.get("multiple_constraint")
    own = {name.casefold() for name in meta.names.values()}
    assert not [alias for alias in meta.aliases if alias.casefold() in own]
    assert "univocalic_lipogram_pair" in meta.aliases
    assert "Compound constraint" in meta.aliases


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
