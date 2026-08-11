"""Generators for haiku. Built from one-syllable words so the count is exact."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Every one of these is a single syllable in CMUdict and under the heuristic,
#: so a line of n of them has exactly n syllables either way.
_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])
PATTERN = [5, 7, 5]


def satisfying() -> CaseStrategy:
    return st.tuples(*[st.lists(_ONE, min_size=n, max_size=n) for n in PATTERN]).map(
        lambda lines: ("\n".join(" ".join(line) for line in lines), {})
    )


def violating() -> CaseStrategy:
    return st.tuples(*[st.lists(_ONE, min_size=n + 1, max_size=n + 1) for n in PATTERN]).map(
        lambda lines: ("\n".join(" ".join(line) for line in lines), {})
    )
