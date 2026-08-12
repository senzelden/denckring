"""Generators for ideenwuerfeln.

The corpus is generated alongside the throw, because a throw only means anything
against the collection it was drawn from. Synthetic throughout.
"""

import json

from hypothesis import strategies as st

from strategies import CaseStrategy

_EXCERPT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=3, max_size=24).map(str.strip)


def _corpus(texts: list[str]) -> str:
    return json.dumps({"entries": [{"text": t} for t in texts]})


def satisfying() -> CaseStrategy:
    return (
        st.lists(_EXCERPT, min_size=3, max_size=8, unique=True)
        .filter(lambda texts: all(texts))
        .map(lambda texts: ("\n".join(texts[:3]), {"source": _corpus(texts)}))
    )


def violating() -> CaseStrategy:
    return (
        st.lists(_EXCERPT, min_size=3, max_size=6, unique=True)
        .filter(lambda texts: all(texts))
        .map(
            lambda texts: (
                "\n".join([*texts[:2], "zzzz nothing wrote this down"]),
                {"source": _corpus(texts)},
            )
        )
    )
