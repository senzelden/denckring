"""Hypothesis generators, one module per procedure.

Each module exposes `satisfying()` and `violating()`, both returning strategies of
`(text, params)` pairs. They are the generator half of every procedure — Batch 1
procedures are restrictive and have no `apply()`, so this is what closes the loop.
"""

from typing import Any

from hypothesis.strategies import SearchStrategy

#: A generated test case: the text, and the params to check it with.
Case = tuple[str, dict[str, Any]]
CaseStrategy = SearchStrategy[Case]

__all__ = ["Case", "CaseStrategy"]
