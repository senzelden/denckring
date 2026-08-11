"""Generators for anagram."""

import random

from hypothesis import strategies as st

from strategies import CaseStrategy

_TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12)


def satisfying() -> CaseStrategy:
    return st.tuples(_TEXT, st.integers(min_value=0, max_value=1000)).map(
        lambda p: (
            "".join(random.Random(p[1]).sample(list(p[0]), len(p[0]))),
            {"source": p[0]},
        )
    )


def violating() -> CaseStrategy:
    return _TEXT.map(lambda source: (source + "z", {"source": source}))
