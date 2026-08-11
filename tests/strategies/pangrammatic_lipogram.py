"""Generators for pangrammatic_lipogram."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WITHOUT_E = "abcdfghijklmnopqrstuvwxyz"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_WITHOUT_E + " ", max_size=20).map(
        lambda extra: (_WITHOUT_E + " " + extra, {"forbidden": "e"})
    )


def violating() -> CaseStrategy:
    return st.text(alphabet=_WITHOUT_E, max_size=20).map(
        lambda body: (body + "e", {"forbidden": "e"})
    )
