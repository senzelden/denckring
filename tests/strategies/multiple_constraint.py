"""Generators for multiple_constraint.

Combines `univocalic` (vowel `e`) and `lipogram` (forbidding `z`) — the same two
already-registered procedures the golden fixture uses — over a consonant alphabet
that excludes every vowel but `e` and excludes `z`, mirroring how
`univocalic_translation`'s own strategy builds a guaranteed-satisfying body.
`violating()` injects two foreign vowels, breaking only the `univocalic` half so
the case fails for the intended reason rather than an incidental one.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_CONSONANTS = "bcdfghjklmnpqrstvwxy"  # no vowel but "e", and no "z"

_PARAMS = {
    "constraints": ["univocalic", "lipogram"],
    "constraint_params": {"univocalic": {"vowel": "e"}, "lipogram": {"forbidden": "z"}},
}


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS + " ", min_size=1, max_size=40).map(
        lambda body: (f"e{body}e", dict(_PARAMS))
    )


def violating() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS + " ", max_size=30).map(
        lambda body: (f"a{body}o", dict(_PARAMS))
    )
