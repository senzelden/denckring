"""Generators for epistrophe."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_HEAD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=12)


def satisfying() -> CaseStrategy:
    return st.lists(_HEAD, min_size=1, max_size=5).map(
        lambda heads: ("\n".join(f"{h} home" for h in heads), {"closing": "home"})
    )


def violating() -> CaseStrategy:
    return st.lists(_HEAD, min_size=1, max_size=4).map(
        lambda heads: (
            "\n".join([f"{h} home" for h in heads] + ["went away"]),
            {"closing": "home"},
        )
    )
