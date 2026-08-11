"""Generators for univocalic. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def satisfying() -> CaseStrategy:
    return st.tuples(
        st.sampled_from("aeiou"), st.text(alphabet=_CONSONANTS + " ", min_size=1, max_size=40)
    ).map(lambda pair: (pair[1] + pair[0] + pair[1], {"vowel": pair[0]}))


def violating() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS + " ", max_size=30).map(
        lambda body: (f"a{body}o", {"vowel": "a"})
    )
