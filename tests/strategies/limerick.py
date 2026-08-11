"""Generators for limerick.

Valid instances of a fixed poetic form cannot be generated blind — the rhyme
families have to be chosen in advance — so these sample from verified texts, as
`sator_square` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """there was an old man with a beard
who said it is just as i feared
two owls and a hen
four larks and a wren
have all flown away and disappeared"""

VIOLATING = """there was an old man with a beard
who said it is just as i feared
two owls and a hen
four larks and a wren
have all built their nests in my beard"""

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, {}))
