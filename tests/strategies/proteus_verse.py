"""Generators for proteus_verse.

A line that permutes cannot be generated blind — most word multisets fill no
metre at all — so these sample from lines verified against the checker, the way
`iambic_pentameter` and `sator_square` do for the same reason.

The satisfying draw is over three lines rather than one because the two halves of
this row's verdict fail independently, and a single sample would exercise only
whichever half that line happens to test.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

PENTAMETER: dict[str, object] = {"metre": "iambic_pentameter"}

CONFORMING: list[tuple[str, dict[str, object]]] = [
    ("the cat can see the moon above the tree", dict(PENTAMETER)),
    ("murmuring beautiful murmuring wonderful murmuring forest", {}),
    ("remember the beloved silver sea", dict(PENTAMETER)),
]

VIOLATING: list[tuple[str, dict[str, object]]] = [
    # Fails on the metre.
    ("the cat sat on the mat", {}),
    # Fails on the count alone: it scans, and admits eight orderings, not nine.
    ("remember the beloved silver sea", {**PENTAMETER, "minimum": 9}),
    # A proteus verse is one line.
    (
        "the cat can see the moon above the tree\nthe dog will run across the field today",
        dict(PENTAMETER),
    ),
]


def satisfying() -> CaseStrategy:
    return st.sampled_from(CONFORMING).map(lambda case: (case[0], dict(case[1])))


def violating() -> CaseStrategy:
    return st.sampled_from(VIOLATING).map(lambda case: (case[0], dict(case[1])))
