"""Generators for prisoners_constraint. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_SAFE = "aceimnorsuvwxz"
_FORBIDDEN = "bdfghjklpqty"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_SAFE + " ", max_size=40).map(lambda text: (text, {}))


def violating() -> CaseStrategy:
    return st.tuples(st.text(alphabet=_SAFE, max_size=20), st.sampled_from(_FORBIDDEN)).map(
        lambda pair: (pair[0] + pair[1], {})
    )
