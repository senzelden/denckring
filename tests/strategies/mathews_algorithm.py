"""Generators for mathews_algorithm."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def _rotate(row: list[str], amount: int) -> list[str]:
    if not row:
        return row
    shift = amount % len(row)
    return row[shift:] + row[:shift]


def _table() -> st.SearchStrategy[list[list[str]]]:
    # Width at least as wide as the row count: row `i`'s shift is then `i`
    # itself (`i % width == i` for every `i < num_rows`), so every row past
    # the first is guaranteed a genuine, nonzero rotation — `unique=True`
    # per row then guarantees that rotation actually reorders it, which
    # `violating()` below relies on.
    def rows(num_rows: int) -> st.SearchStrategy[list[list[str]]]:
        return st.integers(num_rows, num_rows + 3).flatmap(
            lambda width: st.lists(
                st.lists(_WORD, min_size=width, max_size=width, unique=True),
                min_size=num_rows,
                max_size=num_rows,
            )
        )

    return st.integers(2, 4).flatmap(rows)


def satisfying() -> CaseStrategy:
    return _table().map(
        lambda table: (
            "\n".join(" ".join(_rotate(row, index)) for index, row in enumerate(table)),
            {"source": "\n\n".join(" ".join(row) for row in table)},
        )
    )


def violating() -> CaseStrategy:
    """The table read straight across, without rotating any row."""
    return _table().map(
        lambda table: (
            "\n".join(" ".join(row) for row in table),
            {"source": "\n\n".join(" ".join(row) for row in table)},
        )
    )
