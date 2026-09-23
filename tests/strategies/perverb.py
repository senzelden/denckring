"""Corpus grafts, with wrong-donor counterexamples."""

from hypothesis import strategies as st

from strategies import CaseStrategy


def satisfying() -> CaseStrategy:
    return st.just(
        (
            "A stitch in time flock together",
            {
                "source": "A stitch in time saves nine",
                "donor": "Birds of a feather flock together",
            },
        )
    )


def violating() -> CaseStrategy:
    return st.just(
        (
            "A stitch in time gathers no moss",
            {
                "source": "A stitch in time saves nine",
                "donor": "Birds of a feather flock together",
            },
        )
    )
