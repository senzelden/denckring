"""Generators for serial_lipogram. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import CaseStrategy

ALPHABET = string.ascii_lowercase


def _parts(count: int) -> str:
    return "\n\n".join(
        " ".join(ch for ch in ALPHABET if ch != ALPHABET[index]) for index in range(count)
    )


def satisfying() -> CaseStrategy:
    return st.integers(min_value=1, max_value=6).map(lambda n: (_parts(n), {}))


def violating() -> CaseStrategy:
    """Put the forbidden letter back into the first part."""
    return st.integers(min_value=1, max_value=6).map(lambda n: ("a" + _parts(n), {}))
