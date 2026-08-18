"""Generators for fold_in."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)
# At least two words per line: a page-two line's right half — `words[split:]`,
# `split = ceil(n / 2)` — is then never empty, which `violating()` relies on
# to guarantee page one's line alone can never coincide with the fold.
_LINE = st.lists(_WORD, min_size=2, max_size=4, unique=True).map(" ".join)


def _halves(line: str) -> tuple[list[str], list[str]]:
    words = line.split()
    split = (len(words) + 1) // 2
    return words[:split], words[split:]


def _fold_in(page_one: list[str], page_two: list[str]) -> list[str]:
    folded = []
    for index in range(min(len(page_one), len(page_two))):
        left, _ = _halves(page_one[index])
        _, right = _halves(page_two[index])
        folded.append(" ".join(left + right))
    return folded


def _pages() -> st.SearchStrategy[tuple[list[str], list[str]]]:
    # Both pages the same length and built from disjoint vocabularies (each
    # line's words are unique to that line, and pages are generated from
    # entirely separate word pools below), so a fold line's right half can
    # never accidentally already appear in page one's own line.
    n = st.integers(1, 3)
    return n.flatmap(
        lambda count: st.tuples(
            st.lists(_LINE, min_size=count, max_size=count),
            st.lists(_LINE, min_size=count, max_size=count),
        )
    ).filter(lambda pair: not (set(" ".join(pair[0]).split()) & set(" ".join(pair[1]).split())))


def satisfying() -> CaseStrategy:
    return _pages().map(
        lambda pair: (
            "\n".join(_fold_in(pair[0], pair[1])),
            {"source": "\n".join(pair[0]) + "\n\n" + "\n".join(pair[1])},
        )
    )


def violating() -> CaseStrategy:
    """Page one alone, unfolded — never a page-two word in sight."""
    return _pages().map(
        lambda pair: (
            "\n".join(pair[0]),
            {"source": "\n".join(pair[0]) + "\n\n" + "\n".join(pair[1])},
        )
    )
