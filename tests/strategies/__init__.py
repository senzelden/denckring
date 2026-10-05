"""Hypothesis generators, one module per procedure.

Each module exposes `satisfying()` and `violating()`, both returning strategies of
`(text, params)` pairs. They are the generator half of every procedure — Batch 1
procedures are restrictive and have no `apply()`, so this is what closes the loop.
"""

from typing import Any

from hypothesis.strategies import SearchStrategy

from denckring.core.source_compare import is_copy
from denckring.lang import get_pack

#: A generated test case: the text, and the params to check it with.
Case = tuple[str, dict[str, Any]]
CaseStrategy = SearchStrategy[Case]


def not_a_copy(case: Case) -> bool:
    """Whether a case's text is something other than its source's letters in order.

    A source row refuses a copy by default since 0.4.0 (ADR 0055), so a satisfying
    draw that happens to be one (an identity shuffle, a rotation with nothing to
    rotate, a palindrome reversed) is not a satisfying text under the shipped
    parameters. Filtered rather than passed `allow_identity=True`, which would test
    only the lenient reading. Folded, the wider reading: the strategies draw ASCII.
    """
    text, params = case
    return not is_copy(text, params["source"], get_pack("en"), fold=True)


__all__ = ["Case", "CaseStrategy", "not_a_copy"]
