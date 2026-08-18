"""Generators for column_reading."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def _lines(column: int) -> st.SearchStrategy[list[list[str]]]:
    # Every line has at least `column` words, so its `column`th word always exists.
    return st.lists(st.lists(_WORD, min_size=column, max_size=column + 3), min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return (
        st.integers(1, 3)
        .flatmap(lambda column: st.tuples(_lines(column), st.just(column)))
        .map(
            lambda p: (
                " ".join(line[p[1] - 1] for line in p[0]),
                {"source": "\n".join(" ".join(line) for line in p[0]), "column": p[1]},
            )
        )
    )


def violating() -> CaseStrategy:
    """An extra word appended after a valid column reading cannot be in the
    source, once the cursor has advanced past every real word — the same
    trick `diastic` and `mesostic` use."""
    return (
        st.integers(1, 3)
        .flatmap(lambda column: st.tuples(_lines(column), st.just(column)))
        .map(
            lambda p: (
                " ".join([*(line[p[1] - 1] for line in p[0]), "zzzzzzzz"]),
                {"source": "\n".join(" ".join(line) for line in p[0]), "column": p[1]},
            )
        )
    )
