"""Generators for poesie_automat.

Satisfying poems come off the board, which is the only reliable way to get one:
drawn text is essentially never something thirty-six modules can spell.
"""

from hypothesis import strategies as st

from denckring.core import device as devices
from strategies import CaseStrategy

BOARD = devices.load("poesieautomat_2000")


def _spin(seed: int) -> str:
    turned = devices.spin(BOARD, seed)
    lines: dict[int, list[str]] = {number: [] for number in BOARD.lines}
    for slot, flap in zip(BOARD.slots, turned, strict=True):
        lines[slot.line].append(flap)
    return "\n".join(" ".join(lines[number]) for number in BOARD.lines)


def satisfying() -> CaseStrategy:
    return st.integers(min_value=0, max_value=9999).map(lambda seed: (_spin(seed), {}))


def violating() -> CaseStrategy:
    # No flap carries a run of "q", so no module can start on one.
    return st.integers(min_value=0, max_value=9999).map(
        lambda seed: ("\n".join(["qqq qqq", *_spin(seed).splitlines()[1:]]), {})
    )
