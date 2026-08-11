"""Generators for consonantal_lipogram."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_SAFE = "aeioulmnrstvwxyz"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_SAFE + " ", max_size=40).map(lambda text: (text, {"forbidden": "bcd"}))


def violating() -> CaseStrategy:
    return st.tuples(st.text(alphabet=_SAFE, max_size=20), st.sampled_from("bcd")).map(
        lambda p: (p[0] + p[1], {"forbidden": "bcd"})
    )
