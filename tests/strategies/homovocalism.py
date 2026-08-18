"""Generators for homovocalism."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)
_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def _rotate_consonants(word: str) -> str:
    """Change every consonant to the next one; vowels (and their positions) stay put."""
    return "".join(
        _CONSONANTS[(_CONSONANTS.index(c) + 1) % len(_CONSONANTS)] if c in _CONSONANTS else c
        for c in word
    )


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=8).map(
        lambda ws: (" ".join(_rotate_consonants(w) for w in ws), {"source": " ".join(ws)})
    )


def violating() -> CaseStrategy:
    """Extra vowels appended after a verbatim copy of the source guarantee a trailing
    `extra_letters` violation regardless of what the source contains."""
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (" ".join([*ws, "aaaa"]), {"source": " ".join(ws)})
    )
