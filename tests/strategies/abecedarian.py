"""Generators for abecedarian. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_TAIL = st.text(alphabet=_ALPHABET, max_size=4)


def satisfying() -> CaseStrategy:
    return st.integers(min_value=1, max_value=8).flatmap(
        lambda count: st.lists(_TAIL, min_size=count, max_size=count).map(
            lambda tails: (
                "\n".join(_ALPHABET[i] + tail for i, tail in enumerate(tails)),
                {"start": "a"},
            )
        )
    )


def violating() -> CaseStrategy:
    return st.lists(_TAIL, min_size=2, max_size=5).map(
        lambda tails: ("\n".join("z" + tail for tail in tails), {"start": "a"})
    )
