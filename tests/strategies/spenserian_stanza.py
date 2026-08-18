"""Generators for spenserian_stanza.

A valid instance cannot be generated blind — the rhyme families and the closing
alexandrine must be chosen in advance — so these sample verified texts, as
`rhyme_royal` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the birds will sing before the break of day
the fox will hide beneath the fallen stone
the mice will creep beside the ancient way
the owl will call across the dark alone
and now the birds will sing before the day has flown"""

VIOLATING = "\n".join([*CONFORMING.splitlines()[:8], "the rain will fall upon the moor"])

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
