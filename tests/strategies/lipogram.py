"""Generators for lipogram. `satisfying` and `violating` are the module contract."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_LETTERS = "abcdfghijklmnopqrstuvwxyz"  # deliberately without "e"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_LETTERS + " ", min_size=0, max_size=60).map(
        lambda text: (text, {"forbidden": "e"})
    )


def violating() -> CaseStrategy:
    return st.tuples(
        st.text(alphabet=_LETTERS + " ", max_size=30),
        st.text(alphabet=_LETTERS + " ", max_size=30),
    ).map(lambda parts: (parts[0] + "e" + parts[1], {"forbidden": "e"}))
