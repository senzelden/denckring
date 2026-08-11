"""Generators for acrostic. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_TAIL = st.text(alphabet=_ALPHABET, max_size=5)


def satisfying() -> CaseStrategy:
    return st.lists(st.sampled_from(_ALPHABET), min_size=1, max_size=6).flatmap(
        lambda target: st.lists(_TAIL, min_size=len(target), max_size=len(target)).map(
            lambda tails: (
                "\n".join(t + tail for t, tail in zip(target, tails, strict=True)),
                {"target": "".join(target)},
            )
        )
    )


def violating() -> CaseStrategy:
    return st.lists(_TAIL, min_size=2, max_size=4).map(
        lambda tails: ("\n".join("z" + tail for tail in tails), {"target": "a" * len(tails)})
    )
