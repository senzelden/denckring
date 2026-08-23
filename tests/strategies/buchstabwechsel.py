"""Generators for buchstabwechsel.

Built the same way `anagram`'s are — a random letter pool, shuffled with a seeded
`random.Random` for a satisfying case, or perturbed by one surplus letter for a
violating one — with `h` handled separately so the fuzzing itself exercises Rule
II's exemption: the source and the candidate each get their own, independently
chosen, count of `h`s, and a satisfying case still has to pass despite that.
"""

import random

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Every base letter except `h`, which is generated separately below so that a
#: satisfying case can carry a different `h` count on each side.
_TEXT = st.text(alphabet="abcdefgijklmnopqrstuvwxyz", min_size=1, max_size=12)
_H_COUNT = st.integers(min_value=0, max_value=3)


def satisfying() -> CaseStrategy:
    return st.tuples(_TEXT, st.integers(min_value=0, max_value=1000), _H_COUNT, _H_COUNT).map(
        lambda p: (
            "".join(random.Random(p[1]).sample(list(p[0]), len(p[0]))) + "h" * p[3],
            {"source": p[0] + "h" * p[2]},
        )
    )


def violating() -> CaseStrategy:
    return _TEXT.map(lambda source: (source + "z", {"source": source}))
