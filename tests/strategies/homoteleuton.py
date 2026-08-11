"""Generators for homoteleuton."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_STEM = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.lists(_STEM, max_size=6).map(
        lambda stems: (" ".join(s + "y" for s in stems), {"final": "y"})
    )


def violating() -> CaseStrategy:
    return st.lists(_STEM, min_size=1, max_size=4).map(
        lambda stems: (" ".join([s + "y" for s in stems] + ["cat"]), {"final": "y"})
    )
