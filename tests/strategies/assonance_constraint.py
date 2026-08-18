"""Generators for assonance_constraint."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Single-syllable words that all carry the vowel phoneme IY.
_IY_WORDS = st.sampled_from(["tea", "see", "free", "bee", "key", "clean", "meal", "seat"])

#: One word per distinct vowel phoneme (AE, AO, AH, IY, OW, IH), so a line built
#: from a subset of this pool never has two words sharing a vowel.
_DISTINCT_VOWEL_WORDS = st.lists(
    st.sampled_from(["cat", "dog", "jumps", "see", "boat", "king"]),
    unique=True,
    min_size=1,
    max_size=6,
)


def satisfying() -> CaseStrategy:
    return st.lists(_IY_WORDS, min_size=2, max_size=8).map(lambda ws: (" ".join(ws), {}))


def violating() -> CaseStrategy:
    return _DISTINCT_VOWEL_WORDS.map(lambda ws: (" ".join(ws), {}))
