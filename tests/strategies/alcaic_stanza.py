"""Generators for the alcaic stanza."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Verified against CMUdict before use — see the plan's Step 6.
_TROCHEE = st.sampled_from(["forest", "morning", "silver", "garden"])
_DACTYL = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_FREE = st.sampled_from(["and", "the", "of", "in"])

#: `daylight` etc. read `1?` in this pack — the anceps second syllable lets a
#: single word tile two consecutive strong beats, `11`.
_SPONDEE = st.sampled_from(["daylight", "birthright", "moonlight"])

#: A monosyllable, `?`, which fits any single slot — including the strong
#: beats a two-syllable word would otherwise have to supply alone.
_MONO = st.sampled_from(["song", "light", "stone", "sea"])


def satisfying() -> CaseStrategy:
    """Builds each line from words whose stress tiles the pattern exactly,
    using the pattern's own anceps (`?`) slots for the freest words."""
    hendecasyllable = st.tuples(_MONO, _TROCHEE, _SPONDEE, _DACTYL, _TROCHEE, _MONO).map(" ".join)
    enneasyllable = st.tuples(_MONO, _TROCHEE, _TROCHEE, _TROCHEE, _SPONDEE).map(" ".join)
    decasyllable = st.tuples(_DACTYL, _DACTYL, _TROCHEE, _TROCHEE).map(" ".join)
    return st.tuples(hendecasyllable, hendecasyllable, enneasyllable, decasyllable).map(
        lambda ls: ("\n".join(ls), {})
    )


def violating() -> CaseStrategy:
    """Two shapes: the wrong number of lines, and four lines of the wrong
    measure — so both `wrong_line_count` and the metre rules are reached."""
    wrong_count: CaseStrategy = st.lists(_TROCHEE, min_size=2, max_size=3).map(
        lambda ws: ("\n".join(ws), {})
    )
    wrong_measure: CaseStrategy = st.lists(_FREE, min_size=4, max_size=4).map(
        lambda ws: ("\n".join(ws), {})
    )
    return st.one_of(wrong_count, wrong_measure)
