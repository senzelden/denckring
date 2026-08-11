"""Generators for eodermdrome."""

from hypothesis import strategies as st

from strategies import CaseStrategy


def satisfying() -> CaseStrategy:
    # A triangle walk a-b-c-a uses each edge once and returns to its start.
    # Two vertices cannot work: the walk back reuses the single edge.
    return st.lists(
        st.sampled_from("abcdefghijklmnopqrstuvwxyz"), min_size=3, max_size=5, unique=True
    ).map(lambda vs: ("".join([*vs, vs[0]]), {}))


def violating() -> CaseStrategy:
    return st.lists(
        st.sampled_from("abcdefghijklmnopqrstuvwxyz"), min_size=2, max_size=5, unique=True
    ).map(lambda vs: ("".join(vs), {}))
