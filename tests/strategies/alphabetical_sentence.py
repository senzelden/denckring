"""Generators for alphabetical_sentence."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, max_size=8).map(lambda ws: (" ".join(sorted(ws)), {}))


def violating() -> CaseStrategy:
    return st.tuples(_WORD, _WORD).map(lambda p: (f"zzz {p[0]}a {p[1]}", {}))
