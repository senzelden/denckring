"""Generators for haikuization.

These sample a verified source and a verified selection from it rather than
generating blind: the row is `checkability: source`, so a conforming text is not
a property of the text alone — it is exactly the last word of each of the
source's lines, in order, which no blind draw produces.

Not because of the lexicon. An earlier version of this docstring said `check()`
reached `prosody.rhyme_keys` and so needed real dictionary words at each line's
end; ruling R18 removed `phonemes` from the row and the reading with it, and the
row now runs on `tokens` alone — `test_selection_remainder.py::
test_haikuization_tolerates_a_line_end_outside_the_dictionary` pins that an
invented word at a line end produces a report rather than raising.
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
