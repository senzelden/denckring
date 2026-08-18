"""Generators for ghazal.

A valid instance cannot be generated blind — the radif must repeat on every
second line and the qafia before it must rhyme — so these sample verified
texts, as `ballade` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """i cannot find the road tonight
the lamps have all been slowed tonight
the river takes another turn
and leaves its heavy load tonight
the letters that i never sent
are lying in the code tonight"""

#: The radif dropped at its final occurrence.
VIOLATING = "\n".join([*CONFORMING.splitlines()[:5], "are lying in the code today"])

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
