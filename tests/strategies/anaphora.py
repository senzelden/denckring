"""Generators for anaphora."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_TAIL = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=12)


def satisfying() -> CaseStrategy:
    return st.lists(_TAIL, min_size=1, max_size=5).map(
        lambda tails: ("\n".join(f"who {t}" for t in tails), {"opening": "who"})
    )


def violating() -> CaseStrategy:
    return st.lists(_TAIL, min_size=1, max_size=4).map(
        lambda tails: ("\n".join([f"who {t}" for t in tails] + ["whom else"]), {"opening": "who"})
    )
