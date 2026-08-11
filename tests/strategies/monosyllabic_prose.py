"""Generators for monosyllabic_prose."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])
_MANY = st.sampled_from(["water", "silent", "syllable", "elephant"])


def satisfying() -> CaseStrategy:
    return st.lists(_ONE, max_size=10).map(lambda ws: (" ".join(ws), {}))


def violating() -> CaseStrategy:
    return st.tuples(st.lists(_ONE, max_size=6), _MANY).map(lambda p: (" ".join([*p[0], p[1]]), {}))
