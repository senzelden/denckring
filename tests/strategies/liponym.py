"""Generators for liponym."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcefhijklmnpqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, max_size=8).map(lambda ws: (" ".join(ws), {"forbidden": "dog"}))


def violating() -> CaseStrategy:
    return st.lists(_WORD, max_size=5).map(
        lambda ws: (" ".join([*ws, "dog"]), {"forbidden": "dog"})
    )
