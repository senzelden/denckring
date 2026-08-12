"""Generators for n_plus_7.

Instances rest on lexicon membership, which cannot be generated blind — a random
string is almost never a word — so these sample from verified texts, as the fixed
poetic forms do for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the catafalque satchmo on the tablespoonful"""

VIOLATING = """a cat sat on the table"""


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, {"source": "the cat sat on the table"}))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {"source": "the cat sat on the table"}))
