"""Generators for the sapphic stanza."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Verified against CMUdict before use — see the plan's Step 6.
_TROCHEE = st.sampled_from(["forest", "morning", "silver", "garden"])
_DACTYL = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_FREE = st.sampled_from(["and", "the", "of", "in"])


def satisfying() -> CaseStrategy:
    line = st.tuples(_TROCHEE, _TROCHEE, _DACTYL, _TROCHEE, _TROCHEE).map(" ".join)
    adonic = st.tuples(_DACTYL, _TROCHEE).map(" ".join)
    return st.tuples(line, line, line, adonic).map(lambda ls: ("\n".join(ls), {}))


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
