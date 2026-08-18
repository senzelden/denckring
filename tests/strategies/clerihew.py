"""Generators for clerihew.

Valid instances of a fixed poetic form cannot be generated blind — the two rhyme
families have to be chosen in advance — so these sample from a verified text, as
`sonnet` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """sir humphry davy
abominated gravy
he mixed his chemicals every night
and left the lab in the pale light"""

VIOLATING = """sir humphry davy
abominated gravy
he mixed his chemicals every day
and left the lab in the pale light"""

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
