"""Generators for haibun. Built from one-syllable words so counts are exact."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Every one of these is a single syllable in CMUdict and under the heuristic,
#: so a line of n of them has exactly n syllables either way.
_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])
HAIKU = [5, 7, 5]


def _haiku_block() -> st.SearchStrategy[str]:
    return st.tuples(*[st.lists(_ONE, min_size=n, max_size=n) for n in HAIKU]).map(
        lambda lines: "\n".join(" ".join(line) for line in lines)
    )


def _prose_block() -> st.SearchStrategy[str]:
    """A single-line block: never 3 lines, so never mistaken for a haiku."""
    return st.lists(_ONE, min_size=1, max_size=12).map(lambda words: " ".join(words))


def _pair() -> st.SearchStrategy[str]:
    return st.tuples(_prose_block(), _haiku_block()).map(lambda pair: "\n\n".join(pair))


def satisfying() -> CaseStrategy:
    """1 to 3 prose/haiku pairs, prose first each time."""
    return st.integers(min_value=1, max_value=3).flatmap(
        lambda n: st.tuples(*[_pair() for _ in range(n)]).map(
            lambda pairs: ("\n\n".join(pairs), {})
        )
    )


def _missing_haiku() -> CaseStrategy:
    """One or more prose blocks and no haiku anywhere."""
    return st.lists(_prose_block(), min_size=1, max_size=3).map(
        lambda blocks: ("\n\n".join(blocks), {})
    )


def _missing_prose() -> CaseStrategy:
    """One or more haiku blocks and no prose anywhere."""
    return st.lists(_haiku_block(), min_size=1, max_size=3).map(
        lambda blocks: ("\n\n".join(blocks), {})
    )


def _wrong_alternation() -> CaseStrategy:
    """Both kinds of block are present, but the haiku comes before the prose."""
    return st.tuples(_haiku_block(), _prose_block()).map(lambda pair: ("\n\n".join(pair), {}))


def violating() -> CaseStrategy:
    """Reaches `missing_haiku`, `missing_prose` and `wrong_alternation`."""
    return st.one_of(_missing_haiku(), _missing_prose(), _wrong_alternation())
