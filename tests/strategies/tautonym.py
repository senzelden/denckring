"""Generators for tautonym."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_HALF = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=4)


def satisfying() -> CaseStrategy:
    return st.lists(_HALF, max_size=5).map(lambda hs: (" ".join(h + h for h in hs), {}))


def violating() -> CaseStrategy:
    return st.lists(_HALF, min_size=1, max_size=4).map(
        lambda hs: (" ".join([h + h for h in hs] + ["abc"]), {})
    )
