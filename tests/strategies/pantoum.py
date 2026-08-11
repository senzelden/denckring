"""Generators for pantoum."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_LINE = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(_LINE, min_size=6, max_size=6, unique=True).map(
        lambda ls: ("\n".join([ls[0], ls[1], ls[2], ls[3], ls[1], ls[4], ls[3], ls[5]]), {})
    )


def violating() -> CaseStrategy:
    return st.lists(_LINE, min_size=8, max_size=8, unique=True).map(lambda ls: ("\n".join(ls), {}))
