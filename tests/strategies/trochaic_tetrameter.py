"""Generators for trochaic_tetrameter.

Valid instances of a fixed poetic form cannot be generated blind — the rhyme
families have to be chosen in advance — so these sample from verified texts, as
`sator_square` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """never having any water
seldom eating apple butter"""

VIOLATING = """the cat can see the moon above the tree"""

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
