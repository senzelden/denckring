"""Generators for antigram."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Only texts that differ from their own reverse can be a rearrangement of it.
_ASYMMETRIC = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=10).filter(
    lambda word: word != word[::-1]
)


def satisfying() -> CaseStrategy:
    return _ASYMMETRIC.map(lambda word: (word, {"source": word[::-1]}))


def violating() -> CaseStrategy:
    return st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10).map(
        lambda word: (word, {"source": word})
    )
