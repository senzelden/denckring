"""Generators for univocalic_translation. Both must yield (text, params) pairs.

Mirrors `univocalic`'s own generators exactly, since the vowel constraint is the only
checkable half; `source` is added because `SourceParams` requires it, even though
what it names is never verified.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def satisfying() -> CaseStrategy:
    return st.tuples(
        st.sampled_from("aeiou"), st.text(alphabet=_CONSONANTS + " ", min_size=1, max_size=40)
    ).map(lambda pair: (pair[1] + pair[0] + pair[1], {"vowel": pair[0], "source": "x"}))


def violating() -> CaseStrategy:
    return st.text(alphabet=_CONSONANTS + " ", max_size=30).map(
        lambda body: (f"a{body}o", {"vowel": "a", "source": "x"})
    )
