"""Generators for kangaroo_word.

The satisfying case cannot be generated blind — a real hidden synonym has to be
known in advance — so this samples verified pairs, as `rhyme_royal` does.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

PAIRS = [("encourage", "urge"), ("chocolate", "cocoa"), ("rapscallion", "rascal")]


def satisfying() -> CaseStrategy:
    return st.sampled_from(PAIRS).map(lambda pair: (pair[0], {"synonym": pair[1]}))


def violating() -> CaseStrategy:
    return st.just(("encourage", {"synonym": "rug"}))
