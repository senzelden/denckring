"""Generators for snowball_sentence."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


def satisfying() -> CaseStrategy:
    return st.integers(min_value=1, max_value=5).flatmap(
        lambda count: st.lists(
            _WORD, min_size=count * (count + 1) // 2, max_size=count * (count + 1) // 2
        ).map(
            lambda words: (
                " ".join(
                    " ".join(words[i * (i + 1) // 2 : (i + 1) * (i + 2) // 2]) + "."
                    for i in range(count)
                ),
                {},
            )
        )
    )


def violating() -> CaseStrategy:
    return st.tuples(_WORD, _WORD, _WORD).map(
        lambda w: (f"{w[0]}. {w[1]} {w[2]} {w[0]}. {w[1]}.", {})
    )
