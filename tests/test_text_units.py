"""`reading.units` publishes the marks the splitters really use (audit B7).

denckring-bench imported `core.text._CLAUSE_BREAK` so its clause guard would follow
the checker. The published marks replace that import only if they are the
splitters' own, so each is held to its splitter over every character in the Basic
Multilingual Plane: a character is in a unit's marks exactly when it splits `a` from
`b` into two units.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

import denckring
from denckring.core.text import UNIT_ENDS, clause_spans, line_spans, sentence_spans

SPLITTERS: dict[str, Callable[[str], list[tuple[int, str]]]] = {
    "line": line_spans,
    "clause": clause_spans,
    "sentence": sentence_spans,
}


@pytest.mark.parametrize("unit", sorted(SPLITTERS))
def test_each_published_mark_is_exactly_what_splits_the_unit(unit: str) -> None:
    split = SPLITTERS[unit]
    splitting = {
        chr(code)
        for code in range(0x10000)
        if not 0xD800 <= code <= 0xDFFF and len(split(f"a{chr(code)}b")) == 2
    }
    assert splitting == set(UNIT_ENDS[unit])


def test_every_unit_has_a_splitter() -> None:
    assert set(UNIT_ENDS) == set(SPLITTERS)


def test_describe_publishes_the_units() -> None:
    reading = denckring.describe("anaphora").reading
    assert reading.units == UNIT_ENDS
    assert set(",;:\n") <= set(reading.units["clause"])
    assert "\n" not in reading.units["sentence"]
