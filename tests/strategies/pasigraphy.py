"""Generators for pasigraphy.

The table is generated with the throw, because a rendering only means anything
against the vocabulary it crossed.
"""

import json

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=7)


def _table(pairs: list[tuple[str, str]]) -> str:
    return json.dumps(
        {str(i): {"a": here, "b": there} for i, (here, there) in enumerate(pairs, start=1)}
    )


_PAIRS = st.lists(st.tuples(_WORD, _WORD), min_size=1, max_size=5, unique_by=lambda p: p[0])


def satisfying() -> CaseStrategy:
    return _PAIRS.map(
        lambda pairs: (
            " ".join(there for _, there in pairs),
            {
                "source": " ".join(here for here, _ in pairs),
                "table": _table(pairs),
                "from_language": "a",
                "to_language": "b",
            },
        )
    )


def violating() -> CaseStrategy:
    return _PAIRS.map(
        lambda pairs: (
            " ".join(["zzzz" for _ in pairs]),
            {
                "source": " ".join(here for here, _ in pairs),
                "table": _table(pairs),
                "from_language": "a",
                "to_language": "b",
            },
        )
    )
