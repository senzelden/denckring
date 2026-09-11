"""Generators for portmanteau.

Blends cannot be drawn blind — a random coinage is not a blend of anything — so
these sample from pairs measured against the pronouncing dictionaries, the way
every other `phonemes`-requiring row here does.

The violating side covers four distinct rules rather than four ways of tripping
one, because a generator that only ever produced one kind of failure would leave
the others unexercised while looking like coverage.
"""

from typing import Any

from hypothesis import strategies as st

from strategies import CaseStrategy

#: (coinage, host, splice, measured distance).
CONFORMING: list[tuple[str, str, str, float]] = [
    ("Hairitage", "heritage", "hair", 0.000),
    ("Doughnation", "donation", "dough", 0.000),
    ("Combfort", "comfort", "comb", 0.333),
]

#: (coinage, params, the rule it must trip).
VIOLATING: list[tuple[str, dict[str, Any], str]] = [
    ("Heritage", {"source": "heritage", "splice": "hair"}, "splice_not_present"),
    ("Hairitage", {"source": "heritage", "splice": "airit"}, "splice_not_a_word"),
    ("Hairitage", {"source": "bicycle", "splice": "hair"}, "host_unrecoverable"),
    ("Barberella", {"source": "Barbarella", "splice": "barber"}, "unresolvable_pronunciation"),
    # `Breadwinner` really does contain `bread`, and was in the conforming list
    # above until `identical_to_host` arrived and correctly refused it: nothing
    # was spliced, the word already had it. It earns its place here instead.
    ("Breadwinner", {"source": "breadwinner", "splice": "bread"}, "identical_to_host"),
]


def satisfying() -> CaseStrategy:
    return st.sampled_from(
        [(text, {"source": host, "splice": splice}) for text, host, splice, _ in CONFORMING]
    )


def violating() -> CaseStrategy:
    return st.sampled_from([(text, params) for text, params, _ in VIOLATING])
