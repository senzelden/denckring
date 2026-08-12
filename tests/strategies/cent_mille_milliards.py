"""Generators for cent_mille_milliards."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_LINE = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def satisfying() -> CaseStrategy:
    return st.lists(st.tuples(_LINE, _LINE), min_size=1, max_size=5).map(
        lambda rows: (
            "\n".join(first for first, _ in rows),
            {"source": "\n".join(f"{first} | {second}" for first, second in rows)},
        )
    )


def violating() -> CaseStrategy:
    return st.lists(st.tuples(_LINE, _LINE), min_size=1, max_size=4).map(
        lambda rows: (
            "\n".join("zzzz" for _ in rows),
            {"source": "\n".join(f"{first} | {second}" for first, second in rows)},
        )
    )
