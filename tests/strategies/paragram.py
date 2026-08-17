"""Generators for paragram. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import Case, CaseStrategy

LETTERS = string.ascii_lowercase

WORD = st.text(alphabet=LETTERS, min_size=2, max_size=8)


def _swap(word: str, position: int, letter: str) -> str:
    """`word` with one letter at `position` changed to `letter` (or the next
    letter along, if `letter` happened to already be there)."""
    if letter == word[position]:
        letter = LETTERS[(LETTERS.index(letter) + 1) % len(LETTERS)]
    return word[:position] + letter + word[position + 1 :]


def _satisfying_case(word: str, position_seed: int, letter_seed: int) -> Case:
    position = position_seed % len(word)
    letter = LETTERS[letter_seed % len(LETTERS)]
    return f"{word} {_swap(word, position, letter)}", {}


def satisfying() -> CaseStrategy:
    """A word and a one-letter swap of it, at a position and letter that both
    vary — not a fixed index, so the pair found is not always the same shape."""
    return st.tuples(WORD, st.integers(min_value=0), st.integers(min_value=0)).map(
        lambda t: _satisfying_case(*t)
    )


def violating() -> CaseStrategy:
    """Two independent ways to fail to pair, so `violating` exercises more than
    one rule: words of unequal length (never a swap, whatever the suffix), and
    a single word repeated (a word is not paired with itself)."""
    different_length: CaseStrategy = st.tuples(WORD, st.integers(min_value=1, max_value=6)).map(
        lambda t: (f"{t[0]} {t[0] + 'x' * t[1]}", {})
    )
    repeated_word: CaseStrategy = WORD.map(lambda word: (f"{word} {word} {word}", {}))
    return st.one_of(different_length, repeated_word)
