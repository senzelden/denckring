"""Generators for sestina."""

from hypothesis import strategies as st

from denckring.procedures.quenina import spiral
from strategies import CaseStrategy

SIZE = 6


def _build(words: list[str]) -> str:
    permutation = spiral(SIZE)
    stanza = list(words)
    lines = [f"x {w}" for w in stanza]
    for _ in range(SIZE - 1):
        stanza = [stanza[i] for i in permutation]
        lines += [f"x {w}" for w in stanza]
    return "\n".join(lines)


_WORDS = st.lists(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=5),
    min_size=SIZE,
    max_size=SIZE,
    unique=True,
)


def satisfying() -> CaseStrategy:
    return _WORDS.map(lambda words: (_build(words), {}))


def violating() -> CaseStrategy:
    return _WORDS.map(lambda words: ("\n".join(f"x {w}" for w in words * SIZE), {}))
