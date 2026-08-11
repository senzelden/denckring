"""Generators for hendecasyllable."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])
SYLLABLES = 11


def satisfying() -> CaseStrategy:
    return st.lists(
        st.lists(_ONE, min_size=SYLLABLES, max_size=SYLLABLES), min_size=1, max_size=3
    ).map(lambda lines: ("\n".join(" ".join(line) for line in lines), {}))


def violating() -> CaseStrategy:
    return st.lists(
        st.lists(_ONE, min_size=SYLLABLES + 1, max_size=SYLLABLES + 1), min_size=1, max_size=3
    ).map(lambda lines: ("\n".join(" ".join(line) for line in lines), {}))
