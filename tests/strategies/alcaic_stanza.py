"""Generators for the alcaic stanza."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Verified against CMUdict before use — see the plan's Step 6.
_TROCHEE = st.sampled_from(["forest", "morning", "silver", "garden"])
_DACTYL = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_FREE = st.sampled_from(["and", "the", "of", "in"])

#: `daylight` etc. read `1?` in this pack — the anceps second syllable lets a
#: single word tile two consecutive strong beats, `11`. Leading a line, its
#: *first* syllable lands on the anceps instead, so it doubles as the
#: stressed realisation of a line-initial anceps beat.
_SPONDEE = st.sampled_from(["daylight", "birthright", "moonlight"])

#: A monosyllable, `?`, which fits any single slot — including the strong
#: beats a two-syllable word would otherwise have to supply alone.
_MONO = st.sampled_from(["song", "light", "stone", "sea"])

#: `ablate` is `?1` — free then stressed. Swapped in for a trailing trochee,
#: it lands a genuine `1` on a trailing anceps beat instead of the trochee's
#: `0`.
_ANCEPS = st.sampled_from(["ablate"])

#: The hendecasyllable and enneasyllable both open on an anceps beat
#: (index 0). A monosyllable-then-trochee leaves it free; a spondee word
#: followed by a monosyllable lands a genuine stress there instead — the
#: two readings the anceps admits.
_LEAD = st.one_of(st.tuples(_MONO, _TROCHEE), st.tuples(_SPONDEE, _MONO))

#: Either realisation of a trailing anceps beat: unstressed (a trochee) or
#: stressed (`ablate`).
_CLOSE = st.one_of(_TROCHEE, _ANCEPS)


def satisfying() -> CaseStrategy:
    """Builds each line from words whose stress tiles the pattern exactly.
    The anceps beats each draw between their two admissible readings —
    free/unstressed and genuinely stressed — rather than always the same
    one, so `satisfying()` exercises both, not just the unstressed one every
    trochee or monosyllable happens to give."""
    hendecasyllable = st.tuples(_LEAD, _SPONDEE, _DACTYL, _TROCHEE, _MONO).map(
        lambda t: " ".join([*t[0], t[1], t[2], t[3], t[4]])
    )
    enneasyllable = st.tuples(_LEAD, _CLOSE, _TROCHEE, _SPONDEE).map(
        lambda t: " ".join([*t[0], t[1], t[2], t[3]])
    )
    decasyllable = st.tuples(_DACTYL, _DACTYL, _TROCHEE, _CLOSE).map(" ".join)
    return st.tuples(hendecasyllable, hendecasyllable, enneasyllable, decasyllable).map(
        lambda ls: ("\n".join(ls), {})
    )


def violating() -> CaseStrategy:
    """Three shapes, so `wrong_line_count`, `wrong_line_length` and
    `wrong_stress` are all reached: the wrong number of lines, four lines of
    the wrong measure, and a stanza of the right words in the wrong order —
    the same syllable count per line, but the stresses no longer align."""
    wrong_count: CaseStrategy = st.lists(_TROCHEE, min_size=2, max_size=3).map(
        lambda ws: ("\n".join(ws), {})
    )
    wrong_measure: CaseStrategy = st.lists(_FREE, min_size=4, max_size=4).map(
        lambda ws: ("\n".join(ws), {})
    )
    misaligned_hendecasyllable = st.tuples(_MONO, _TROCHEE, _DACTYL, _SPONDEE, _TROCHEE, _MONO).map(
        " ".join
    )
    misaligned_enneasyllable = st.tuples(_MONO, _TROCHEE, _SPONDEE, _TROCHEE, _TROCHEE).map(
        " ".join
    )
    misaligned_decasyllable = st.tuples(_TROCHEE, _TROCHEE, _DACTYL, _DACTYL).map(" ".join)
    wrong_stress: CaseStrategy = st.tuples(
        misaligned_hendecasyllable,
        misaligned_hendecasyllable,
        misaligned_enneasyllable,
        misaligned_decasyllable,
    ).map(lambda ls: ("\n".join(ls), {}))
    return st.one_of(wrong_count, wrong_measure, wrong_stress)
