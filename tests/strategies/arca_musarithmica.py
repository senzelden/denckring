"""Generators for arca_musarithmica.

The tablet is generated with the setting, because a setting only means anything
against the box it was drawn from. Phrases are built from one-syllable words so
the indexing is exact either side of the data package.
"""

import json

from hypothesis import strategies as st

from strategies import CaseStrategy

_ONE = st.sampled_from(["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"])
_PATTERN = st.text(alphabet="12345 ", min_size=3, max_size=9).map(str.strip).filter(bool)


def _case(lengths: list[int], patterns: list[str]) -> tuple[str, dict[str, str]]:
    tablet = {str(n): [p] for n, p in zip(lengths, patterns, strict=True)}
    phrases = ["a " * (n - 1) + "cat" for n in lengths]
    return (
        "\n".join(patterns),
        {"source": "\n".join(phrases), "pinakes": json.dumps(tablet)},
    )


_LENGTHS = st.lists(st.integers(2, 6), min_size=1, max_size=3, unique=True)


def satisfying() -> CaseStrategy:
    return _LENGTHS.flatmap(
        lambda lengths: st.lists(
            _PATTERN, min_size=len(lengths), max_size=len(lengths), unique=True
        ).map(lambda patterns: _case(lengths, patterns))
    )


def violating() -> CaseStrategy:
    return _LENGTHS.flatmap(
        lambda lengths: st.lists(
            _PATTERN, min_size=len(lengths), max_size=len(lengths), unique=True
        ).map(
            lambda patterns: (
                "\n".join("9 9 9 9 9" for _ in patterns),
                _case(lengths, patterns)[1],
            )
        )
    )
