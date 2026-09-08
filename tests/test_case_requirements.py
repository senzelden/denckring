"""A case may need more than its row does, and must say so.

`alexandrine` requires `syllables.heuristic`, which every pack has, so it runs
everywhere. But the Gryphius case's *verdict* depends on the German pronouncing
dictionary: with it, one line reads fourteen syllables and the case fails as
recorded; without it the heuristic counts twelve and the same text satisfies.

A fixture whose expectation flips with the installed data is not evidence, and it
ships — `eval --all` on a bare `pip install denckring` reported one failure that
was not a capability gap. The explorer's own suite is what caught it, because it
asserts that every failure in a minimal install is blocked rather than red.
"""

from __future__ import annotations

from denckring.eval.harness import GoldenCase, unmet_requirements
from denckring.lang import get_pack


def test_a_case_needing_nothing_extra_is_never_blocked() -> None:
    case = GoldenCase(procedure="palindrome", name="x", text="level", satisfied=True)
    assert unmet_requirements(case, get_pack("en")) == []


def test_a_case_may_require_more_than_its_row_does() -> None:
    """The row asks for the heuristic; this case asks for the dictionary."""
    case = GoldenCase(
        procedure="alexandrine",
        name="x",
        text="x",
        satisfied=False,
        requires=["syllables.dictionary"],
    )
    assert unmet_requirements(case, get_pack("en")) == []


def test_an_unavailable_requirement_is_named() -> None:
    case = GoldenCase(
        procedure="alexandrine", name="x", text="x", satisfied=False, requires=["stress"]
    )
    assert unmet_requirements(case, get_pack("fr")) == ["stress"]
