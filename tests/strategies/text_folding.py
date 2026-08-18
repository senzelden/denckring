"""Generators for text_folding."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def _fold(lines: list[str], fold_at: int) -> list[str]:
    cut = min(max(fold_at, 0), len(lines))
    return lines[cut:] + lines[:cut]


def _lines_and_fold() -> st.SearchStrategy[tuple[list[str], int]]:
    # `unique=True` and `fold_at` strictly between the flaps: the far flap is
    # never empty, so its first line — now the folded reading's first line —
    # is never the source's own first line, and `violating()` below can rely
    # on that to guarantee a mismatch.
    return st.lists(_WORD, min_size=2, max_size=8, unique=True).flatmap(
        lambda lines: st.tuples(st.just(lines), st.integers(1, len(lines) - 1))
    )


def satisfying() -> CaseStrategy:
    return _lines_and_fold().map(
        lambda p: (
            "\n".join(_fold(p[0], p[1])),
            {"source": "\n".join(p[0]), "fold_at": p[1]},
        )
    )


def violating() -> CaseStrategy:
    """The source read straight through, unfolded, against its own fold."""
    return _lines_and_fold().map(
        lambda p: (
            "\n".join(p[0]),
            {"source": "\n".join(p[0]), "fold_at": p[1]},
        )
    )
