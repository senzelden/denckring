"""Generators for hemeling.

A compound constraint cannot be generated blind — the anagram and the rhyme have
to be arranged together — so these sample from texts verified against the
checker, as `iambic_pentameter` and `sator_square` do for the same reason.

The violating draw covers both halves separately, because either can fail on its
own and a single sample would exercise only one of them.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

GLOSS = "the letters of your name will turn and then\nthey say a truer thing than they did when"

CONFORMING = [
    (f"listen\n{GLOSS}", {"source": "silent"}),
    (f"enlist\n{GLOSS}", {"source": "silent"}),
]

VIOLATING = [
    # The rhyme fails and the anagram holds.
    (
        "listen\nthe letters of your name will turn and then\n"
        "they say a truer thing than they did now",
        {"source": "silent"},
    ),
    # The anagram fails and the rhyme holds.
    (f"listens\n{GLOSS}", {"source": "silent"}),
    # No explication at all, which is the half this row exists for.
    ("listen", {"source": "silent"}),
]


def satisfying() -> CaseStrategy:
    return st.sampled_from(CONFORMING).map(lambda case: (case[0], dict(case[1])))


def violating() -> CaseStrategy:
    return st.sampled_from(VIOLATING).map(lambda case: (case[0], dict(case[1])))
