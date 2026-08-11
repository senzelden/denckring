"""Generators for every_nth_word."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.tuples(st.lists(_WORD, min_size=1, max_size=12), st.integers(2, 4)).map(
        lambda p: (" ".join(p[0][p[1] - 1 :: p[1]]), {"source": " ".join(p[0]), "n": p[1]})
    )


def violating() -> CaseStrategy:
    return st.lists(_WORD, min_size=4, max_size=10).map(
        lambda ws: (" ".join(ws), {"source": " ".join(ws), "n": 2})
    )
