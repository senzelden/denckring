"""Generators for the elegiac couplet."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Each maps to exactly one stress pattern in CMUdict, verified before use.
#: `murmuring` etc. are `100`; `forest` etc. are `10`.
_DACTYL_WORD = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_TROCHEE_WORD = st.sampled_from(["forest", "morning", "silver", "garden"])
_STRESSED = st.sampled_from(["song", "light", "stone", "sea"])

#: CMUdict marks secondary stress, which this pack renders as `?` — so a
#: "spondee word" reads `1?` rather than `11` and fits the spondee slot
#: through the free second syllable. `shipwreck` is deliberately absent: it
#: is `10`, which does not fit `11`.
_SPONDEE_WORD = st.sampled_from(["daylight", "birthright", "moonlight"])

#: A foot that may spell either half of a substitutable slot.
_SUBSTITUTABLE_FOOT = st.one_of(_DACTYL_WORD, _SPONDEE_WORD)


def _hexameter(dactyls: list[str], close: str) -> str:
    return " ".join([*dactyls, close])


def satisfying() -> CaseStrategy:
    """Hexameter feet 1-4 and pentameter feet 1-2 each independently a dactyl
    or a spondee word, so every draw exercises whichever of the 32 hexameter
    readings and 4 pentameter readings its choices happen to spell, rather
    than always the same one. The fixed positions — hexameter foot 5,
    hexameter foot 6, and the pentameter's second hemiepes — never vary,
    because the pattern set does not admit substitution there."""
    strategy: CaseStrategy = st.tuples(
        st.lists(_SUBSTITUTABLE_FOOT, min_size=4, max_size=4),
        _DACTYL_WORD,
        st.one_of(_SPONDEE_WORD, _TROCHEE_WORD),
        st.lists(_SUBSTITUTABLE_FOOT, min_size=2, max_size=2),
        _STRESSED,
        st.lists(_DACTYL_WORD, min_size=2, max_size=2),
        _STRESSED,
    ).map(
        lambda parts: (
            _hexameter([*parts[0], parts[1]], parts[2])
            + "\n"
            + " ".join([*parts[3], parts[4], *parts[5], parts[6]]),
            {},
        )
    )
    return strategy


def violating() -> CaseStrategy:
    """Two shapes: an odd line count, and a couplet whose second line scans as
    a hexameter rather than a pentameter."""
    odd: CaseStrategy = st.lists(_DACTYL_WORD, min_size=5, max_size=5).flatmap(
        lambda dactyls: _TROCHEE_WORD.map(lambda close: (_hexameter(dactyls, close), {}))
    )
    both_hexameters: CaseStrategy = st.lists(_DACTYL_WORD, min_size=5, max_size=5).flatmap(
        lambda dactyls: _TROCHEE_WORD.map(
            lambda close: (_hexameter(dactyls, close) + "\n" + _hexameter(dactyls, close), {})
        )
    )
    return st.one_of(odd, both_hexameters)
