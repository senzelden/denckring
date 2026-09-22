"""Known OEWN pairs and unchanged counterexamples."""

from hypothesis import strategies as st

from strategies import CaseStrategy


def satisfying() -> CaseStrategy:
    return st.just(("large little", {"source": "big small"}))


def violating() -> CaseStrategy:
    return st.just(("big small", {"source": "big small"}))
