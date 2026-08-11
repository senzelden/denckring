"""Generators for cut_up."""

import random

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.tuples(st.lists(_WORD, min_size=1, max_size=8), st.integers(0, 999)).map(
        lambda p: (
            " ".join(random.Random(p[1]).sample(p[0], len(p[0]))),
            {"source": " ".join(p[0])},
        )
    )


def violating() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (" ".join([*ws, "zzzz"]), {"source": " ".join(ws)})
    )
