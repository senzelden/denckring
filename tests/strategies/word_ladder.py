"""Generators for word_ladder.

Instances rest on lexicon membership, which cannot be generated blind — a
random one-letter change is almost never a word — so these sample from a
verified ladder, as `charade` and `tmesis` do for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = "cold cord card ward warm"

#: Same words as the satisfying case, reordered so "card" to "warm" changes
#: two letters at once instead of one.
VIOLATING = "cold card warm"


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, {}))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
