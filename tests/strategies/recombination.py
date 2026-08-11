"""Generators for recombination."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_SENTENCE = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(_SENTENCE, min_size=1, max_size=5, unique=True).map(
        lambda ss: (
            " ".join(s + "." for s in reversed(ss)),
            {"source": " ".join(s + "." for s in ss)},
        )
    )


def violating() -> CaseStrategy:
    return st.lists(_SENTENCE, min_size=1, max_size=4, unique=True).map(
        lambda ss: (
            " ".join(s + "." for s in ss),
            {"source": " ".join(s + "." for s in [*ss, "zzz"])},
        )
    )
