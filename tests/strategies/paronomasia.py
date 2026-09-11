"""Generators for paronomasia.

Every pair here is measured against CMUdict rather than guessed at, and the
distances are written down beside them, because the whole row turns on where a
pair falls relative to the band. A blind generator could not produce these: two
random words are almost never within half a phoneme-edit of each other, which is
the same reason `spoonerism` and the other `phonemes`-requiring rows sample from
verified text instead.

The violating side deliberately fails for *four different rules* rather than
four ways of hitting one. A generator that only ever produced out-of-band pairs
would leave `no_displacement`, `unrecoverable` and `unresolvable_pronunciation`
unexercised while looking like coverage.
"""

from typing import Any

from hypothesis import strategies as st

from strategies import CaseStrategy

#: (text, source, measured distance). Each displaces exactly one word, inside
#: the default band of 0.0 to 0.5.
CONFORMING: list[tuple[str, str, float]] = [
    ("Bread Pitt", "Brad Pitt", 0.250),
    ("Brand Pitt", "Brad Pitt", 0.200),
    ("Knead to Know", "Need to Know", 0.000),
    ("Hairy Potter", "Harry Potter", 0.000),
    ("Curl up and dye", "Curl up and die", 0.000),
    ("the cut in the hat", "the cat in the hat", 0.333),
]

#: (text, source, params, the rule it must trip). `Any` on the params, as on
#: `strategies.Case`, because these are forwarded as `**kwargs` into `check`.
VIOLATING: list[tuple[str, str, dict[str, Any], str]] = [
    # Nothing displaced at all.
    ("Brad Pitt", "Brad Pitt", {}, "no_displacement"),
    # Displaced past the ceiling: `Pitt` and `Brad` share no phoneme.
    ("Pitt Pitt", "Brad Pitt", {"max_distance": 0.25}, "distance_out_of_band"),
    # Displaced below the floor: a homophone, where a forced pun was asked for.
    ("Hairy Potter", "Harry Potter", {"min_distance": 0.2}, "distance_out_of_band"),
    # Two words displaced where one was allowed — `pit` and `pitt` are one sound.
    ("Bread Pit", "Brad Pitt", {}, "unrecoverable"),
    # The coined surface no pronouncing dictionary carries.
    ("British Hairways", "British Airways", {}, "unresolvable_pronunciation"),
    # A phrase of a different length is not a displacement of this one.
    ("Bread Pitt Junior", "Brad Pitt", {}, "length_mismatch"),
]


def satisfying() -> CaseStrategy:
    return st.sampled_from([(text, {"source": source}) for text, source, _ in CONFORMING])


def violating() -> CaseStrategy:
    return st.sampled_from(
        [(text, {"source": source, **params}) for text, source, params, _ in VIOLATING]
    )
