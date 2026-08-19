"""Generators for tmesis.

Instances rest on lexicon membership, which cannot be generated blind — a random
hyphenated string is almost never a word once the middle piece is removed — so
these sample from verified texts, as `charade` and `word_square` do for the same
reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = "abso-bloody-lutely"

#: Three hyphen-joined tokens, same shape as the satisfying case, but the halves
#: ("cats", "dogs") do not rejoin into a word the lexicon knows.
VIOLATING = "cats-really-dogs"


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, {}))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
