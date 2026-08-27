"""The generator's requirements are not the checker's.

`anagram` checks with core alone and generates only with a word lexicon. One
`requires` list could not say both, so the generator's need went undeclared and
`missing` reported nothing — the defect this file pins.
"""

import pytest

from denckring import check, describe
from denckring.core import catalogue
from denckring.core.describe import apply_runnable
from denckring.lang.en import EnglishPack


def test_anagram_declares_the_lexicon_its_generator_uses() -> None:
    assert "lexicon.words" in catalogue.get("anagram").apply_requires


def test_declaring_it_does_not_gate_the_checker() -> None:
    """The whole reason it could not go in `requires`. A core-only install must
    still check an anagram."""
    assert "lexicon.words" not in catalogue.get("anagram").requires
    report = check("anagram", "silent", source="listen")
    assert report.satisfied


def test_apply_runnable_reports_what_the_generator_lacks() -> None:
    meta = catalogue.get("anagram")
    core_only = EnglishPack()
    assert "lexicon.words" not in core_only.capabilities
    ok, missing = apply_runnable(meta, pack=core_only)
    assert not ok
    assert missing == ["lexicon.words"]


def test_apply_missing_reaches_the_description() -> None:
    described = describe("anagram")
    assert hasattr(described, "apply_missing")
    assert isinstance(described.apply_missing, list)


def test_rows_without_a_generator_requirement_default_to_empty() -> None:
    assert catalogue.get("lipogram").apply_requires == []


#: pytest's own "pid" spelling, not "procedure_id" — the shared conftest's
#: `pytest_generate_tests` auto-parametrizes any test whose fixturenames
#: include the literal name `procedure_id` across every *registered*
#: procedure, which collides with an explicit `@pytest.mark.parametrize` of
#: the same name and would raise `duplicate parametrization of 'procedure_id'`
#: at collection time. These rows are not all registered anyway.
@pytest.mark.parametrize("pid", sorted(catalogue.ids()))
def test_apply_requires_names_only_real_capabilities(pid: str) -> None:
    """Matches the existing rule for `requires`: a capability no pack can answer
    is a promise the catalogue cannot keep."""
    known = {
        "tokens", "alphabet", "fold_diacritics", "letter_shapes",
        "syllables", "syllables.heuristic", "syllables.dictionary",
        "phonemes", "stress", "lexicon.words", "lexicon.nouns", "lexicon.glosses",
    }
    assert set(catalogue.get(pid).apply_requires) <= known
