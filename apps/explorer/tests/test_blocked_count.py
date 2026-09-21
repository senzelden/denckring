"""The figure two docstrings quote, measured instead of remembered.

`board.py` and `test_board.py` both say "54 of the 158 tiles" are `blocked` on a
partial install. That number was true when written and nothing checked it since,
which is the shape of every stale count this project has had to chase. Asserting
it here means a change that moves it reports itself.

Not a target: if this goes red, the number in the two docstrings is what changes,
not the board.
"""

from __future__ import annotations

from explorer import board
from test_board import partial_install  # noqa: F401 - the fixture, used below


def test_the_blocked_tile_count_is_the_one_the_docstrings_quote(
    partial_install: None,  # noqa: F811
) -> None:
    states = [tile.state for tile in board.tiles()]
    blocked = states.count("blocked")
    assert len(states) == 158, "the catalogue changed size; both docstrings quote 158"
    assert blocked == 54, (
        f"{blocked} tiles are blocked on the simulated install, not 54 — update the "
        f"docstrings in explorer/board.py and tests/test_board.py to match"
    )
