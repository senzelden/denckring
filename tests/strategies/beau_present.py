"""Generators for beau_present. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_NAME = "marcel"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_NAME + " ", max_size=40).map(lambda text: (text, {"name": _NAME}))


def violating() -> CaseStrategy:
    return st.tuples(st.text(alphabet=_NAME, max_size=20), st.sampled_from("bdfgh")).map(
        lambda pair: (pair[0] + pair[1], {"name": _NAME})
    )
