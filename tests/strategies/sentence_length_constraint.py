"""Generators for sentence_length_constraint."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.lists(st.lists(_WORD, min_size=3, max_size=3), min_size=1, max_size=4).map(
        lambda ss: (" ".join(" ".join(s) + "." for s in ss), {"words": 3})
    )


def violating() -> CaseStrategy:
    return st.lists(_WORD, min_size=5, max_size=5).map(
        lambda ws: (" ".join(ws) + ".", {"words": 3})
    )
