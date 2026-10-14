"""Every letter rule declares German (ADR 0063).

ADR 0047 widened `languages` only where a row's own `source` named an
attestation in that language, and over German that test returns zero. ADR 0063
adds a second, narrower ground for one class of row: a *letter rule* — a row
whose checker reads letters and nothing else — is orthographic, so declaring
`de` claims that the rule is checked in German, not that German literature
attests the form.

The class is defined mechanically, so the guard computes it from the catalogue
rather than carrying a list that a new row could slip past: `family` is
`letter` and `requires` is a subset of `{tokens, alphabet, fold_diacritics}`.
A row that also consults a lexicon, a pronunciation or a letter-shape table is
outside the class — `kangaroo_word` (`lexicon.words`) is the boundary case the
ADR names — and stays as ADR 0047 left it.

Only registered rows are held to it: the declaration promises a German golden
case (`test_every_declared_language_has_a_golden_case`), which a row with no
checker cannot have.
"""

from __future__ import annotations

from denckring.core.protocol import Meta
from denckring.core.registry import all_procedures

#: The capabilities a checker may require and still read letters only (ADR 0063).
LETTER_ONLY = frozenset({"tokens", "alphabet", "fold_diacritics"})


def _is_letter_rule(meta: Meta) -> bool:
    return meta.family == "letter" and set(meta.requires) <= LETTER_ONLY


def _letter_rules() -> list[Meta]:
    return [proc.meta for proc in all_procedures().values() if _is_letter_rule(proc.meta)]


def test_the_criterion_selects_rows() -> None:
    """A criterion that matched nothing would make the guard below pass vacuously."""
    assert _letter_rules(), "no registered row is a letter rule by ADR 0063's criterion"


def test_every_letter_rule_declares_german() -> None:
    missing = sorted(meta.id for meta in _letter_rules() if "de" not in meta.languages)
    assert not missing, (
        f"{missing} read letters only (family `letter`, requires within "
        f"{sorted(LETTER_ONLY)}) but do not declare `de`. A letter rule is checked in "
        f"German by construction, so it declares German — with a German name, "
        f"definition and golden case (ADR 0063)"
    )
