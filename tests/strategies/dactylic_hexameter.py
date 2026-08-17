"""Generators for dactylic hexameter, built from words of known stress."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Each maps to exactly one stress pattern in CMUdict, verified before use.
#: `murmuring` etc. are `100`; `forest` etc. are `10`.
_DACTYL_WORD = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_TROCHEE_WORD = st.sampled_from(["forest", "morning", "silver", "garden"])

#: CMUdict marks secondary stress, which this pack renders as `?` — so a
#: "spondee word" reads `1?` rather than `11` and fits the spondee slot through
#: the free second syllable. `shipwreck` is deliberately absent: it is `10`,
#: which does not fit `11`.
_SPONDEE_WORD = st.sampled_from(["daylight", "birthright", "moonlight"])


def _line(dactyls: list[str], close: str) -> str:
    return " ".join([*dactyls, close])


def satisfying() -> CaseStrategy:
    """Five dactyls and a trochee — the commonest reading, and always 17
    syllables, so no substitution ambiguity can creep in."""
    return st.lists(_DACTYL_WORD, min_size=5, max_size=5).flatmap(
        lambda dactyls: _TROCHEE_WORD.map(lambda close: (_line(dactyls, close), {}))
    )


def violating() -> CaseStrategy:
    """Two shapes, so both reachable rules are generated: a line of the wrong
    length, and a line of the right length whose stresses fall wrong."""
    too_short: CaseStrategy = st.lists(_DACTYL_WORD, min_size=2, max_size=3).map(
        lambda words: (" ".join(words), {})
    )
    wrong_stress: CaseStrategy = st.lists(_TROCHEE_WORD, min_size=8, max_size=8).map(
        lambda words: (" ".join(words), {})
    )
    return st.one_of(too_short, wrong_stress)
