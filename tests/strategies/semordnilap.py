"""Generators for semordnilap.

Instances rest on lexicon membership, which cannot be generated blind — a random
string is almost never a word — so these sample from verified texts, as the fixed
poetic forms do for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """stressed"""

VIOLATING = """level"""


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, {}))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
