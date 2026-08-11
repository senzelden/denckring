"""Generators for supervocalic."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def satisfying() -> CaseStrategy:
    return st.permutations("aeiou").map(lambda vowels: (" ".join(f"{v}n" for v in vowels), {}))


def violating() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS + " ", max_size=20).map(lambda body: (body + "a", {}))
