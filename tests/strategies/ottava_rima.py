"""Generators for ottava_rima.

A valid instance cannot be generated blind — the rhyme families must be chosen in
advance — so these sample verified texts, as `rhyme_royal` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the owl will call across the dark at sea
the fox will hide beneath the fallen way
the mice will creep beside the ancient stone
the birds will sing before the day has flown"""

VIOLATING = "\n".join(CONFORMING.splitlines()[:7])

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
