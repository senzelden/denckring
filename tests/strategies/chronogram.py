"""Generators for chronogram."""

from hypothesis import strategies as st

from strategies import CaseStrategy

VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def satisfying() -> CaseStrategy:
    return st.lists(st.sampled_from("ivxlcdm"), min_size=1, max_size=8).map(
        lambda letters: ("".join(letters), {"year": sum(VALUES[c] for c in letters)})
    )


def violating() -> CaseStrategy:
    return st.lists(st.sampled_from("ivxlcdm"), min_size=1, max_size=8).map(
        lambda letters: ("".join(letters), {"year": sum(VALUES[c] for c in letters) + 1})
    )
