"""Generators for cut_up."""

import random

from hypothesis import strategies as st

from strategies import CaseStrategy, not_a_copy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.tuples(st.lists(_WORD, min_size=1, max_size=8), st.integers(0, 999)).map(
        lambda p: (
            " ".join(random.Random(p[1]).sample(p[0], len(p[0]))),
            {"source": " ".join(p[0])},
        )
    ).filter(not_a_copy) | st.just(("word", {"source": "word"}))  # R-U2a: one word


def violating() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (" ".join([*ws, "zzzz"]), {"source": " ".join(ws)})
    )
