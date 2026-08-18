"""Generators for boustrophedon."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_LETTERS = "abcdefghijklmnopqrstuvwxyz"
_WORD = st.text(alphabet=_LETTERS, min_size=1, max_size=5)

# Two distinct letters, so the line can never equal its own reverse: `violating()`
# needs every odd-indexed line to genuinely fail `line_not_turned` when left
# untouched, and a one-character or palindromic line would pass by accident.
_NON_PALINDROME = (
    st.tuples(st.sampled_from(_LETTERS), st.sampled_from(_LETTERS))
    .filter(lambda pair: pair[0] != pair[1])
    .map(lambda pair: pair[0] + pair[1])
)


def _turn(lines: list[str]) -> list[str]:
    return [line[::-1] if index % 2 == 1 else line for index, line in enumerate(lines)]


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda lines: ("\n".join(_turn(lines)), {"source": "\n".join(lines)})
    )


def violating() -> CaseStrategy:
    """At least two lines, none of them turned: the source itself is what is
    checked, so every odd-indexed line — guaranteed non-palindromic — fails
    `line_not_turned`."""
    return st.lists(_NON_PALINDROME, min_size=2, max_size=6).map(
        lambda lines: ("\n".join(lines), {"source": "\n".join(lines)})
    )
