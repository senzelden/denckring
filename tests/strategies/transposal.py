"""Generators for transposal."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=5).map(
        lambda ws: (" ".join(w[::-1] for w in ws), {"source": " ".join(ws)})
    )


def violating() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=4).map(
        lambda ws: (" ".join([*ws, "zz"]), {"source": " ".join([*ws, "ab"])})
    )
