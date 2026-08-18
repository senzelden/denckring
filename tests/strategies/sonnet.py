"""Generators for sonnet.

A valid instance cannot be generated blind — the rhyme families must be chosen in
advance — so these sample verified texts, as `rhyme_royal` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the fox will hide beneath the fallen stone
the fish will swim beneath the frozen lake
the owl will call across the dark alone
the deer will wake before the morning break
the moon will rise and fill the sky with light
the horse will stand beside the gate so still
the stars will burn until the end of night
the mouse will hide behind the open till
the clock will mark the passing of the time
the bell will ring and slowly start to chime"""

VIOLATING = "\n".join(CONFORMING.splitlines()[:13])

PARAMS: dict[str, object] = {"scheme": "ABABCDCDEFEFGG", "metre": "0101010101"}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
