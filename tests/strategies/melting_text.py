"""Generators for melting_text."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (" ".join(ws[::2]), {"source": " ".join(ws)})
    )


def violating() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=5).map(
        lambda ws: (" ".join([*ws, "zzz"]), {"source": " ".join(ws)})
    )
