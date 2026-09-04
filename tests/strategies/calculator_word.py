"""Generators for calculator_word.

The words are a fixed list rather than drawn from the lexicon, and each was
verified against `pack.is_word` before being written down. Composing a text
letter by letter would produce almost nothing the lexicon knows, and the row
asks the lexicon by default — `require_words` is the escape, and testing only
through it would leave the interesting half of the checker unexercised.

The digits are computed by `to_digits`, never written by hand: a hand-computed
digit string is precisely the plausible-looking value this project's notes warn
about, and one wrong one in a strategy would fail on a shrunk example far from
its cause.
"""

from hypothesis import strategies as st

from denckring.core.calculator import to_digits
from strategies import CaseStrategy

#: English words the display can write, each confirmed present in the pack's
#: lexicon on 2026-09-04.
_WRITABLE = [
    "hello",
    "shell",
    "globe",
    "bless",
    "bell",
    "boil",
    "hobbies",
    "oboe",
    "geese",
    "loose",
    "soil",
    "hose",
    "isles",
    "eggshell",
    "bogie",
]

#: Words the display cannot write, each carrying at least one letter outside
#: BEGHILOS, and each confirmed present in the lexicon — so the violation is the
#: mapping and never the lexicon.
_UNWRITABLE = ["cat", "dogma", "music", "pizza", "vertex"]


def satisfying() -> CaseStrategy:
    return st.sampled_from(_WRITABLE).map(lambda word: (word, {"digits": to_digits(word)}))


def violating() -> CaseStrategy:
    """Both ways a single word can fail: an unwritable letter, and a correct
    word against digits that spell something else."""
    unwritable = st.sampled_from(_UNWRITABLE).map(lambda word: (word, {"digits": "7353"}))
    mismatched = st.sampled_from(_WRITABLE).map(
        lambda word: (word, {"digits": to_digits("bogie" if word != "bogie" else "hello")})
    )
    return st.one_of(unwritable, mismatched)
