"""Generators for rhyme_royal.

Valid instances of a fixed poetic form cannot be generated blind — the rhyme
families have to be chosen in advance — so these sample from verified texts, as
`sator_square` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the birds will sing before the break of day
the fox will hide beneath the fallen stone
the owl will call across the dark alone"""

VIOLATING = """the cat can see the moon above the tree
a bird can fly around the house at three
the cat can see the moon above the tree
a bird can fly around the house at three"""

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
