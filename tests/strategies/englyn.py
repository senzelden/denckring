"""Generators for englyn.

Valid instances of a fixed poetic form cannot be generated blind — the syllable
pattern and the single shared rhyme have to be chosen in advance — so these sample
from a verified text, as `haiku`'s neighbours do when a scheme is involved.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the summer evening settles by the bay
beside the quiet way
and the swallow calls the day
and the river hums today"""

VIOLATING = "\n".join(["a short first line", *CONFORMING.splitlines()[1:]])

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
