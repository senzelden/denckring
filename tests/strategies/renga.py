"""Generators for renga. Built from one-syllable words so counts are exact."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Every one of these is a single syllable in CMUdict and under the heuristic,
#: so a line of n of them has exactly n syllables either way.
_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])
HOKKU = [5, 7, 5]
WAKIKU = [7, 7]


def _stanza(pattern: list[int]) -> st.SearchStrategy[str]:
    return st.tuples(*[st.lists(_ONE, min_size=n, max_size=n) for n in pattern]).map(
        lambda lines: "\n".join(" ".join(line) for line in lines)
    )


def _shape(index: int) -> list[int]:
    return HOKKU if index % 2 == 0 else WAKIKU


def _chain(n: int) -> st.SearchStrategy[str]:
    stanzas = [_stanza(_shape(i)) for i in range(n)]
    return st.tuples(*stanzas).map(lambda parts: "\n\n".join(parts))


def satisfying() -> CaseStrategy:
    """A chain of 2 to 5 stanzas, alternating 5-7-5 and 7-7, starting on a hokku."""
    return st.integers(min_value=2, max_value=5).flatmap(
        lambda n: _chain(n).map(lambda text: (text, {}))
    )


def _too_few_links() -> CaseStrategy:
    """A single well-formed hokku — a renga needs at least two linked stanzas."""
    return _stanza(HOKKU).map(lambda text: (text, {}))


def _wrong_stanza_shape() -> CaseStrategy:
    """A chain where one stanza's line count doesn't match its slot's shape."""

    def build(n: int, bad_index: int, extra: bool) -> CaseStrategy:
        wanted = _shape(bad_index)
        bad_pattern = [*wanted, 5] if extra else wanted[:-1]
        stanzas = [_stanza(bad_pattern) if i == bad_index else _stanza(_shape(i)) for i in range(n)]
        return st.tuples(*stanzas).map(lambda parts: ("\n\n".join(parts), {}))

    picks: st.SearchStrategy[tuple[int, int, bool]] = st.integers(min_value=2, max_value=4).flatmap(
        lambda n: st.tuples(st.just(n), st.integers(min_value=0, max_value=n - 1), st.booleans())
    )
    return picks.flatmap(lambda pick: build(*pick))


def violating() -> CaseStrategy:
    """Reaches both `too_few_links` and `wrong_stanza_shape`."""
    return st.one_of(_too_few_links(), _wrong_stanza_shape())
