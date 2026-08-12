"""Generators for llull_figure."""

from hypothesis import strategies as st

from denckring.core import device as devices
from strategies import CaseStrategy

FIGURE = devices.load_figure("llull_ternary")
CHAMBERS = FIGURE.chambers(3)


def satisfying() -> CaseStrategy:
    return st.sampled_from(CHAMBERS).flatmap(
        lambda chamber: st.sampled_from([*FIGURE.level_names(), None]).map(
            lambda level: (
                chamber if level is None else " ".join(FIGURE.read(chamber, level)),
                {},
            )
        )
    )


def violating() -> CaseStrategy:
    # A letter outside the nine cannot name a principle at any level.
    return st.sampled_from(CHAMBERS).map(lambda chamber: (chamber[:-1] + "Z", {}))
