"""Generators for monoconsonantal."""

from hypothesis import strategies as st

from strategies import CaseStrategy


def satisfying() -> CaseStrategy:
    return st.text(alphabet="aeioun ", max_size=40).map(lambda text: (text, {"consonant": "n"}))


def violating() -> CaseStrategy:
    return st.text(alphabet="aeioun", max_size=20).map(
        lambda body: (body + "t", {"consonant": "n"})
    )
