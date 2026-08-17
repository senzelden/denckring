"""Generators for pangrammatic_window. `satisfying` and `violating` are the contract."""

import string

from hypothesis import strategies as st

from strategies import Case, CaseStrategy

ALPHABET = string.ascii_lowercase


def _padded(extra: int, filler: str) -> Case:
    """All 26 letters plus `extra` more of `filler`, with a bar sized to hold it
    exactly — varies both the padding amount and which letter pads it."""
    text = ALPHABET + filler * extra
    return text, {"max_length": len(ALPHABET) + extra}


def satisfying() -> CaseStrategy:
    return st.tuples(
        st.integers(min_value=0, max_value=20),
        st.sampled_from(ALPHABET),
    ).map(lambda pair: _padded(*pair))


def _missing_a_letter(dropped: int) -> Case:
    """25 of the 26 letters, well inside a generous bar: `missing_letter` alone."""
    letter = ALPHABET[dropped]
    return ALPHABET.replace(letter, ""), {"max_length": 100}


def _over_the_bar(extra: int) -> Case:
    """All 26 letters, padded past the minimum bar: `window_too_long` alone."""
    return ALPHABET + "a" * (extra + 1), {"max_length": len(ALPHABET)}


def violating() -> CaseStrategy:
    """Draws among two spoilers, so both `missing_letter` and `window_too_long`
    are reached rather than just the first one tried."""
    return st.one_of(
        st.integers(min_value=0, max_value=25).map(_missing_a_letter),
        st.integers(min_value=0, max_value=20).map(_over_the_bar),
    )
