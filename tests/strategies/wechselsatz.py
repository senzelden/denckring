"""Generators for wechselsatz."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(st.tuples(_WORD, _WORD), min_size=1, max_size=5).map(
        lambda slots: (
            " ".join(first for first, _ in slots),
            {"source": " ".join(f"{first}|{second}" for first, second in slots)},
        )
    )


def violating() -> CaseStrategy:
    return st.lists(st.tuples(_WORD, _WORD), min_size=1, max_size=4).map(
        lambda slots: (
            " ".join("zzzz" for _ in slots),
            {"source": " ".join(f"{first}|{second}" for first, second in slots)},
        )
    )
