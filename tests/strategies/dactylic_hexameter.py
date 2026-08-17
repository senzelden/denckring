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
    """Draws among the readings the pattern set actually admits: feet 1-4 each
    independently a dactyl or a spondee word, foot 5 fixed as a dactyl (per
    the classical convention `feet()` encodes), and foot 6 a spondee or a
    trochee word. Every draw exercises whichever of the 32 `PATTERNS` its
    choices happen to spell, rather than always the same one."""
    substitutable_foot = st.one_of(_DACTYL_WORD, _SPONDEE_WORD)
    final_foot = st.one_of(_SPONDEE_WORD, _TROCHEE_WORD)
    return st.tuples(
        st.lists(substitutable_foot, min_size=4, max_size=4), _DACTYL_WORD, final_foot
    ).map(lambda parts: (_line([*parts[0], parts[1]], parts[2]), {}))


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
