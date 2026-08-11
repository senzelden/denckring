"""Generators for tautogram. Both must yield (text, params) pairs."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_TAIL = st.text(alphabet=_ALPHABET, min_size=0, max_size=6)


def satisfying() -> CaseStrategy:
    return st.tuples(st.sampled_from(_ALPHABET), st.lists(_TAIL, max_size=6)).map(
        lambda pair: (" ".join(pair[0] + tail for tail in pair[1]), {"initial": pair[0]})
    )


def violating() -> CaseStrategy:
    return st.lists(_TAIL, min_size=1, max_size=5).map(
        lambda tails: (" ".join(["p" + t for t in tails] + ["zebra"]), {"initial": "p"})
    )
