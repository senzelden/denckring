"""Generators for fold_in."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def _fold_in(page_one: list[str], page_two: list[str]) -> list[str]:
    folded: list[str] = []
    for index in range(max(len(page_one), len(page_two))):
        if index < len(page_one):
            folded.append(page_one[index])
        if index < len(page_two):
            folded.append(page_two[index])
    return folded


def _pages() -> st.SearchStrategy[tuple[list[str], list[str]]]:
    # `unique=True` and page one holding at least two lines: `violating()` below
    # relies on the straight concatenation's second line (page one's own
    # second line) never coinciding with the interleaved reading's second
    # line (page two's first), which uniqueness across the whole split
    # guarantees.
    return st.lists(_WORD, min_size=3, max_size=9, unique=True).flatmap(
        lambda words: st.integers(2, len(words) - 1).map(lambda cut: (words[:cut], words[cut:]))
    )


def satisfying() -> CaseStrategy:
    return _pages().map(
        lambda pair: (
            "\n".join(_fold_in(pair[0], pair[1])),
            {"source": "\n".join(pair[0]) + "\n\n" + "\n".join(pair[1])},
        )
    )


def violating() -> CaseStrategy:
    """Both pages, concatenated straight through rather than interleaved."""
    return _pages().map(
        lambda pair: (
            "\n".join(pair[0] + pair[1]),
            {"source": "\n".join(pair[0]) + "\n\n" + "\n".join(pair[1])},
        )
    )
