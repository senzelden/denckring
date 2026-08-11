"""Generators for reverse_snowball. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def _word(length: int) -> st.SearchStrategy[str]:
    return st.text(alphabet=_ALPHABET, min_size=length, max_size=length)


def satisfying() -> CaseStrategy:
    return (
        st.integers(min_value=1, max_value=6)
        .flatmap(lambda count: st.tuples(*[_word(count - i) for i in range(count)]))
        .map(lambda words: (" ".join(words), {}))
    )


def violating() -> CaseStrategy:
    return st.tuples(_word(3), _word(3), _word(1)).map(lambda words: (" ".join(words), {}))
