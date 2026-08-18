"""Generators for curtal_sonnet.

Valid instances of a fixed poetic form cannot be generated blind — the rhyme
families have to be chosen in advance — so these sample from a verified text, as
`sonnet` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the fish will swim beneath the frozen lake
the cat can see the moon above the tree
the dog will run across the field today
the deer will wake before the morning break
a bird can fly around the house at three
the sun will set behind the hill in may
the moon will rise and fill the sky with light
the boat will drift below the open sea
the wind will move the grass and blow away
the stars will burn until the end of night
the birds will sing before the break of day"""

VIOLATING = "\n".join(CONFORMING.splitlines()[:10])

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
