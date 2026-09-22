"""`kind` is a claim about the form; `constructive` is a claim about the install.

Ten rows say `kind: both` and have no generator behind them. Rewriting `kind`
would trade a true statement about the form for a true statement about the
install and lose the first, so both are reported.

The tenth is `homosyntaxism` (ADR 0045), and how it arrived is the reason
`test_the_list_is_complete` now exists. The list below was maintained by hand
and nothing compared it to the registry, so adding a row that belongs on it left
every test here green and the docstring above saying "Nine". A list that only
fails when somebody notices is not a guard.
"""

from denckring import describe, summaries
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

WITHOUT_GENERATORS = {
    "buchstabwechsel",
    "definitional_expansion",
    "definitional_literature",
    "homoconsonantism",
    "homosyntaxism",
    "homovocalism",
    "larding",
    "lipogrammatic_translation",
    "tmesis",
    "univocalic_translation",
}


def test_the_ten_say_both_things_at_once() -> None:
    for procedure_id in sorted(WITHOUT_GENERATORS):
        described = describe(procedure_id)
        assert described.kind in {"constructive", "both"}, procedure_id
        assert described.constructive is False, procedure_id


def test_the_list_is_complete() -> None:
    """Derived from the registry, so a row added to the catalogue cannot go
    missing from the list the way `homosyntaxism` did.

    The rule, not the answer: *every* row claiming it can generate and shipping
    no generator is named here. That is what the list is for, and a count on its
    own could be satisfied by the wrong ten.
    """
    actual = {
        procedure_id
        for procedure_id in all_procedures()
        if describe(procedure_id).kind in {"constructive", "both"}
        and describe(procedure_id).constructive is False
    }
    assert actual == WITHOUT_GENERATORS


def test_summaries_carry_it_too() -> None:
    rows = {row.id: row for row in summaries()}
    assert rows["anagram"].constructive is True
    assert rows["homoconsonantism"].constructive is False


def test_the_count_of_generators_is_thirty_three() -> None:
    """`apply_procedure`'s docstring claimed sixteen. Pin the real number so the
    prose cannot drift from it again. Twenty-seven until `proteus_verse` landed,
    twenty-eight until `calculator_word`, twenty-nine until `paronomasia`, and
    thirty until `portmanteau` grew one, thirty-one until `chimera` landed.
    `amphibologia` briefly made it thirty-two and was cut; see ADR 0043.
    Perverb adds a deterministic corpus graft (ADR 0048)."""
    generators = [p for p in all_procedures().values() if isinstance(p, Constructive)]
    assert len(generators) == 33
