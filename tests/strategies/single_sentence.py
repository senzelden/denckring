"""Generators for single_sentence."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_CLAUSE = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=30)


def satisfying() -> CaseStrategy:
    return _CLAUSE.map(lambda clause: (clause + ".", {}))


def violating() -> CaseStrategy:
    return st.tuples(_CLAUSE, _CLAUSE).map(lambda p: (f"{p[0]}. {p[1]}.", {}))
