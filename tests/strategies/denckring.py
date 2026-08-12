"""Generators for denckring.

Satisfying words are produced by turning the rings, which is the only reliable
way to get one: a random string is essentially never spellable by the device.
"""

from hypothesis import strategies as st

from denckring.core import device as devices
from strategies import CaseStrategy

RINGS = devices.load("harsdoerffer_1651")


def satisfying() -> CaseStrategy:
    return st.integers(min_value=0, max_value=9999).map(
        lambda seed: ("".join(devices.spin(RINGS, seed)) or "Lang", {})
    )


def violating() -> CaseStrategy:
    # No ring carries "q" other than as part of a cluster that needs a vowel
    # after it, so a run of them cannot be segmented.
    return st.integers(min_value=2, max_value=8).map(lambda n: ("qq" * n, {}))
