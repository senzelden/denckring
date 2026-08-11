"""Generators for syllable_count."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])


def satisfying() -> CaseStrategy:
    return st.lists(st.integers(1, 6), min_size=1, max_size=4).flatmap(
        lambda pattern: st.tuples(*[st.lists(_ONE, min_size=n, max_size=n) for n in pattern]).map(
            lambda lines: (
                "\n".join(" ".join(line) for line in lines),
                {"pattern": pattern},
            )
        )
    )


def violating() -> CaseStrategy:
    return st.lists(st.integers(1, 5), min_size=1, max_size=3).flatmap(
        lambda pattern: st.tuples(
            *[st.lists(_ONE, min_size=n + 1, max_size=n + 1) for n in pattern]
        ).map(
            lambda lines: (
                "\n".join(" ".join(line) for line in lines),
                {"pattern": pattern},
            )
        )
    )
