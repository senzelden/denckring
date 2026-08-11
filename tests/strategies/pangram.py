"""Generators for pangram. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_ALPHABET + " ", max_size=20).map(
        lambda extra: (_ALPHABET + " " + extra, {})
    )


def violating() -> CaseStrategy:
    return st.sampled_from(_ALPHABET).map(lambda dropped: (_ALPHABET.replace(dropped, ""), {}))
