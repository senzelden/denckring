"""Generators for sator_square."""

from hypothesis import strategies as st

from strategies import CaseStrategy

SATOR = "sator\narepo\ntenet\nopera\nrotas"


def satisfying() -> CaseStrategy:
    # Symmetric squares are hard to generate blind; the attested one plus the
    # trivial single-letter square cover both ends of the size range.
    return st.sampled_from([SATOR, "a"]).map(lambda grid: (grid, {}))


def violating() -> CaseStrategy:
    return st.lists(st.text(alphabet="ab", min_size=2, max_size=2), min_size=2, max_size=2).map(
        lambda rows: ("\n".join(["ab", "ab"]), {})
    )
