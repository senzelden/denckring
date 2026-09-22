"""Known OEWN pairs and unchanged counterexamples."""

from hypothesis import strategies as st

from strategies import CaseStrategy


def satisfying() -> CaseStrategy:
    return st.just(("cold small", {"source": "hot big"}))


def violating() -> CaseStrategy:
    return st.just(("hot big", {"source": "hot big"}))
