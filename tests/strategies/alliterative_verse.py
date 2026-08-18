"""Generators for alliterative_verse."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Every word here starts on the same folded initial, "b".
_B_WORDS = st.sampled_from(["bright", "bank", "birds", "bold", "brave", "bear", "boat", "bell"])

#: Distinct initials from one another and from "b", so at most one of each can
#: ever land in a generated line.
_OTHER_WORDS = st.lists(
    st.sampled_from(["cat", "dog", "egg", "fish", "goat", "hat", "ice", "jam"]),
    unique=True,
    max_size=5,
)


def satisfying() -> CaseStrategy:
    return st.lists(_B_WORDS, min_size=3, max_size=8).map(lambda ws: (" ".join(ws), {}))


def violating() -> CaseStrategy:
    return _OTHER_WORDS.map(lambda others: (" ".join(["bright", "bank", *others]), {}))
