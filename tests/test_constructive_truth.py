"""`kind` is a claim about the form; `constructive` is a claim about the install.

Nine rows say `kind: both` and have no generator behind them. Rewriting `kind`
would trade a true statement about the form for a true statement about the
install and lose the first, so both are reported.
"""

from denckring import describe, summaries
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

WITHOUT_GENERATORS = {
    "buchstabwechsel",
    "definitional_expansion",
    "definitional_literature",
    "homoconsonantism",
    "homovocalism",
    "larding",
    "lipogrammatic_translation",
    "tmesis",
    "univocalic_translation",
}


def test_the_nine_say_both_things_at_once() -> None:
    for procedure_id in sorted(WITHOUT_GENERATORS):
        described = describe(procedure_id)
        assert described.kind in {"constructive", "both"}, procedure_id
        assert described.constructive is False, procedure_id


def test_summaries_carry_it_too() -> None:
    rows = {row.id: row for row in summaries()}
    assert rows["anagram"].constructive is True
    assert rows["homoconsonantism"].constructive is False


def test_the_count_of_generators_is_twenty_nine() -> None:
    """`apply_procedure`'s docstring claimed sixteen. Pin the real number so the
    prose cannot drift from it again. Twenty-seven until `proteus_verse` landed,
    twenty-eight until `calculator_word`."""
    generators = [p for p in all_procedures().values() if isinstance(p, Constructive)]
    assert len(generators) == 29
