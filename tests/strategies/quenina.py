"""Generators for quenina."""

from hypothesis import strategies as st

from denckring.procedures.quenina import is_valid_size, spiral
from strategies import CaseStrategy

_SIZES = [n for n in range(1, 10) if is_valid_size(n)]


def _build(size: int, words: list[str]) -> str:
    permutation = spiral(size)
    stanza = words[:size]
    lines = [f"x {w}" for w in stanza]
    for _ in range(size - 1):
        stanza = [stanza[i] for i in permutation]
        lines += [f"x {w}" for w in stanza]
    return "\n".join(lines)


def satisfying() -> CaseStrategy:
    return st.sampled_from(_SIZES).map(
        lambda size: (_build(size, [chr(ord("a") + i) * 2 for i in range(size)]), {"n": size})
    )


def violating() -> CaseStrategy:
    return st.sampled_from([n for n in _SIZES if n > 2]).map(
        lambda size: (
            "\n".join("x " + chr(ord("a") + (i % size)) * 2 for i in range(size * size)),
            {"n": size},
        )
    )
