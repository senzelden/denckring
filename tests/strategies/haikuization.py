"""Generators for haikuization.

Real dictionary words are required at the end of each line: `check()` reaches
`prosody.rhyme_keys`, which looks up a rhyme key for that word and raises
`MissingCapability` for a word the lexicon has never seen. So these sample a
verified text rather than generating blind, as `rhyme_scheme` and `ballade`
do for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

SOURCE = """the cat sat down
a dog ran fast
one bird flew high"""


def satisfying() -> CaseStrategy:
    return st.just(("down fast high", {"source": SOURCE}))


def violating() -> CaseStrategy:
    """The first word swapped for a word that is not its line's end."""
    return st.just(("cat fast high", {"source": SOURCE}))
