"""Generators for spoonerism.

Instances rest on the pronouncing dictionary, which cannot be generated blind —
a random pair of words is as likely to share an onset as not — so these sample
from verified texts, as the other `phonemes`-requiring rows do for the same
reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: "cat" (onset K) and "dog" (onset D): distinct onsets, a genuine exchange.
CONFORMING = "cat dog"

#: "cat" and "cap" both carry the onset K: swapping it changes nothing.
VIOLATING = "cat cap"


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, {}))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
