"""Generators for palindrome. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def satisfying() -> CaseStrategy:
    return st.tuples(st.text(alphabet=_ALPHABET, max_size=12), st.sampled_from(["", "x"])).map(
        lambda pair: (pair[0] + pair[1] + pair[0][::-1], {})
    )


def violating() -> CaseStrategy:
    return st.text(alphabet=_ALPHABET, min_size=1, max_size=12).map(
        lambda body: ("a" + body + "b", {})
    )
