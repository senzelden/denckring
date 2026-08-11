"""Generators for heterogram. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def satisfying() -> CaseStrategy:
    return st.lists(st.sampled_from(_ALPHABET), unique=True, max_size=26).map(
        lambda letters: ("".join(letters), {})
    )


def violating() -> CaseStrategy:
    return st.tuples(st.sampled_from(_ALPHABET), st.text(alphabet=" ", max_size=3)).map(
        lambda pair: (pair[0] + pair[1] + pair[0], {})
    )
