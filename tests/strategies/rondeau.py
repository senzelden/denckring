"""Generators for rondeau.

A valid instance cannot be generated blind — the two rhyme families have to be
held constant across all thirteen full lines, and the rentrement repeated
verbatim at lines 9 and 15 — so these sample verified texts, as `ballade` does
for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the summer holds the door
the tiles lie warm upon the floor
a single swallow crosses sky
no one can say the reason why
the garden waits for something more
the bread is kept inside the store
the boats are drawn along the shore
a distant gull begins to cry
the summer holds
the thunder starts its far off roar
the candle burns an hour before
the wind goes past with one long sigh
the truth is not one to deny
the harvest time will soon restore
the summer holds"""

#: The rentrement broken at its middle occurrence.
VIOLATING = "\n".join(
    [*CONFORMING.splitlines()[:8], "the winter holds", *CONFORMING.splitlines()[9:]]
)

PARAMS: dict[str, object] = {"rentrement_words": 3}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
