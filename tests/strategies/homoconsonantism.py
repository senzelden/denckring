"""Generators for homoconsonantism."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)
_VOWELS = "aeiou"


def _rotate_vowels(word: str) -> str:
    """Change every vowel to the next one; consonants (and their positions) stay put."""
    return "".join(
        _VOWELS[(_VOWELS.index(c) + 1) % len(_VOWELS)] if c in _VOWELS else c for c in word
    )


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=8).map(
        lambda ws: (" ".join(_rotate_vowels(w) for w in ws), {"source": " ".join(ws)})
    )


def violating() -> CaseStrategy:
    """Extra consonants appended after a verbatim copy of the source guarantee a
    trailing `extra_letters` violation regardless of what the source contains."""
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (" ".join([*ws, "zzzz"]), {"source": " ".join(ws)})
    )
