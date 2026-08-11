"""Generators for telestich. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_HEAD = st.text(alphabet=_ALPHABET, max_size=5)


def satisfying() -> CaseStrategy:
    return st.lists(st.sampled_from(_ALPHABET), min_size=1, max_size=6).flatmap(
        lambda target: st.lists(_HEAD, min_size=len(target), max_size=len(target)).map(
            lambda heads: (
                "\n".join(head + t for t, head in zip(target, heads, strict=True)),
                {"target": "".join(target)},
            )
        )
    )


def violating() -> CaseStrategy:
    return st.lists(_HEAD, min_size=2, max_size=4).map(
        lambda heads: ("\n".join(head + "z" for head in heads), {"target": "a" * len(heads)})
    )
