"""Generators for serial_lipogram. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import Case, CaseStrategy

ALPHABET = string.ascii_lowercase


def _word_avoiding(letter: str) -> str:
    """A short word that never contains `letter` — the constraint is pure
    absence, so it need not use any of the other 25 letters either."""
    filler = "b" if letter != "b" else "c"
    return filler * 3


def _parts_avoiding(forbidden: list[str]) -> str:
    return "\n\n".join(_word_avoiding(letter) for letter in forbidden)


def satisfying() -> CaseStrategy:
    """Exactly one part per letter of the alphabet, walking from a random start."""

    def build(start_index: int) -> Case:
        forbidden = [ALPHABET[(start_index + i) % len(ALPHABET)] for i in range(len(ALPHABET))]
        return _parts_avoiding(forbidden), {"start": ALPHABET[start_index]}

    return st.integers(min_value=0, max_value=len(ALPHABET) - 1).map(build)


def _wrong_count(part_count: int) -> Case:
    """Every present part is correct, but there are not exactly 26 of them."""
    forbidden = [ALPHABET[i % len(ALPHABET)] for i in range(part_count)]
    return _parts_avoiding(forbidden), {}


def _forbidden_letter(bad_index: int) -> Case:
    """The full 26 parts, one of them keeping the letter it should omit."""
    words = [_word_avoiding(letter) for letter in ALPHABET]
    words[bad_index] = ALPHABET[bad_index] * 3
    return "\n\n".join(words), {}


def violating() -> CaseStrategy:
    """Reaches both violation rules: a wrong part count, and a kept letter."""
    return st.one_of(
        st.integers(min_value=0, max_value=25).map(_wrong_count),
        st.integers(min_value=27, max_value=31).map(_wrong_count),
        st.integers(min_value=0, max_value=len(ALPHABET) - 1).map(_forbidden_letter),
    )
