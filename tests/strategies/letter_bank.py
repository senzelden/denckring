"""Generators for letter_bank."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_BANK = "meandr"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_BANK, max_size=30).map(
        lambda text: (_BANK + " " + text, {"bank": _BANK})
    )


def violating() -> CaseStrategy:
    return st.text(alphabet=_BANK, max_size=20).map(
        lambda body: (_BANK + body + "z", {"bank": _BANK})
    )
