"""Every procedure as one tile, coloured by its own golden cases.

`denckring eval` prints 344 lines and a scoreboard, which is the right shape for CI
and the wrong shape for a person looking for the one row that is unhappy. Same data,
laid out so it can be scanned.
"""

from __future__ import annotations

from dataclasses import dataclass

from denckring.core import catalogue
from denckring.core.registry import all_procedures
from denckring.eval import harness


@dataclass(frozen=True)
class Tile:
    """One procedure on the board."""

    id: str
    name: str
    family: str
    #: `green` — every golden case passes. `red` — at least one does not.
    #: `grey` — catalogued but not implemented, which is a gap and not a failure.
    state: str
    cases: int
    #: The first failing case, named, or empty when there is nothing to say.
    detail: str


def tiles() -> list[Tile]:
    """Every catalogued procedure, with its golden cases run."""
    scoreboard = harness.run()
    implemented = set(all_procedures())
    by_procedure: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for result in scoreboard.results:
        counts[result.procedure] = counts.get(result.procedure, 0) + 1
        if not result.passed:
            by_procedure.setdefault(result.procedure, []).append(
                f"{result.case}: {result.detail or 'did not match'}"
            )

    out: list[Tile] = []
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        failures = by_procedure.get(procedure_id, [])
        state = "grey" if procedure_id not in implemented else ("red" if failures else "green")
        out.append(
            Tile(
                id=procedure_id,
                name=meta.names.get("en", procedure_id),
                family=meta.family,
                state=state,
                cases=counts.get(procedure_id, 0),
                detail=failures[0] if failures else "",
            )
        )
    return out


def scoreboard_line() -> str:
    """The line `denckring status` prints, for the board to carry unchanged."""
    return harness.status().line()
