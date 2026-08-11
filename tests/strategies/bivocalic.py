"""Generators for bivocalic."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS + "ae ", max_size=40).map(
        lambda text: (text, {"vowels": "ae"})
    )


def violating() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS, max_size=20).map(
        lambda body: (body + "io", {"vowels": "ae"})
    )
