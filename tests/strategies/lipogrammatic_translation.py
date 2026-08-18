"""Generators for lipogrammatic_translation. Both must yield (text, params) pairs.

Mirrors `lipogram`'s own generators exactly, since the missing-letter constraint is
the only checkable half; `source` is added because `SourceParams` requires it, even
though what it names is never verified.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_LETTERS = "abcdfghijklmnopqrstuvwxyz"  # deliberately without "e"


def satisfying() -> CaseStrategy:
    return st.text(alphabet=_LETTERS + " ", min_size=0, max_size=60).map(
        lambda text: (text, {"forbidden": "e", "source": "x"})
    )


def violating() -> CaseStrategy:
    return st.tuples(
        st.text(alphabet=_LETTERS + " ", max_size=30),
        st.text(alphabet=_LETTERS + " ", max_size=30),
    ).map(lambda parts: (parts[0] + "e" + parts[1], {"forbidden": "e", "source": "x"}))
