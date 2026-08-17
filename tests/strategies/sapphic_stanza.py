"""Generators for the sapphic stanza."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Verified against CMUdict before use — see the plan's Step 6.
_TROCHEE = st.sampled_from(["forest", "morning", "silver", "garden"])
_DACTYL = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_FREE = st.sampled_from(["and", "the", "of", "in"])

#: `ablate` is `?1` — free then stressed. Swapped in for the trochee that
#: ends on one of the hendecasyllable's two anceps beats (index 3 and index
#: 10) or the adonic's (index 4), it lands a genuine `1` there instead of the
#: trochee's `0` — the other reading the anceps admits.
_ANCEPS = st.sampled_from(["ablate"])

#: Either realisation of an anceps-ending foot: unstressed (a trochee) or
#: stressed (`ablate`).
_CLOSE = st.one_of(_TROCHEE, _ANCEPS)


def satisfying() -> CaseStrategy:
    """Ties each anceps beat to a strategy of its own two admissible
    readings, so `satisfying()` exercises both rather than only the
    unstressed one every trochee word happens to give."""
    line = st.tuples(_TROCHEE, _CLOSE, _DACTYL, _TROCHEE, _CLOSE).map(" ".join)
    adonic = st.tuples(_DACTYL, _CLOSE).map(" ".join)
    return st.tuples(line, line, line, adonic).map(lambda ls: ("\n".join(ls), {}))


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
    misaligned_line = st.tuples(_DACTYL, _TROCHEE, _TROCHEE, _TROCHEE, _TROCHEE).map(" ".join)
    misaligned_adonic = st.tuples(_TROCHEE, _DACTYL).map(" ".join)
    wrong_stress: CaseStrategy = st.tuples(
        misaligned_line, misaligned_line, misaligned_line, misaligned_adonic
    ).map(lambda ls: ("\n".join(ls), {}))
    return st.one_of(wrong_count, wrong_measure, wrong_stress)
