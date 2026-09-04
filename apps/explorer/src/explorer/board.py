"""Every procedure as one tile, coloured by its own golden cases.

`denckring eval` prints 344 lines and a scoreboard, which is the right shape for CI
and the wrong shape for a person looking for the one row that is unhappy. Same data,
laid out so it can be scanned.
"""

from __future__ import annotations

from dataclasses import dataclass

from denckring.core import catalogue
from denckring.core.describe import runnable
from denckring.core.errors import extra_for
from denckring.core.registry import all_procedures
from denckring.eval import harness


@dataclass(frozen=True)
class Tile:
    """One procedure on the board."""

    id: str
    name: str
    family: str
    #: `green` — every golden case passes. `red` — at least one genuinely does
    #: not. `blocked` — every failure is a capability this install lacks, which
    #: is data missing rather than a checker that is wrong. `grey` — catalogued
    #: but not implemented, which is a gap and not a failure either.
    #:
    #: `blocked` was `red` until 2026-09-04, and on a `denckring[en,de]` install
    #: that is 52 of the 156 tiles — every one of them a row whose data is simply
    #: not here. `denckring eval --all` reports 0 failed on a full install at the
    #: same moment, so the board was the only surface calling them failures.
    state: str
    cases: int
    #: What to say under the tile. For `blocked`, the remedy alone — `requires
    #: denckring[fr]` — because the full `missing_capability` message repeats the
    #: procedure id and the capability, both of which are already on the tile.
    #: For `red`, the failing case and why.
    detail: str


def tiles() -> list[Tile]:
    """Every catalogued procedure, with its golden cases run."""
    scoreboard = harness.run()
    implemented = set(all_procedures())
    failed: dict[str, list[harness.CaseResult]] = {}
    counts: dict[str, int] = {}
    for result in scoreboard.results:
        counts[result.procedure] = counts.get(result.procedure, 0) + 1
        if not result.passed:
            failed.setdefault(result.procedure, []).append(result)

    out: list[Tile] = []
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        failures = failed.get(procedure_id, [])
        if procedure_id not in implemented:
            state, detail = "grey", ""
        elif not failures:
            state, detail = "green", ""
        elif all(result.code == "missing_capability" for result in failures):
            # Read from `CaseResult.code`, never by matching the message. The
            # raiser already knew this was a capability gap; recovering it from
            # English prose breaks the moment the wording changes, which is the
            # trap `stage.word_ladder`'s own docstring names.
            state, detail = "blocked", _blocked_by(failures)
        else:
            first = failures[0]
            state = "red"
            detail = f"{first.case}: {first.detail or 'did not match'}"
        out.append(
            Tile(
                id=procedure_id,
                name=meta.names.get("en", procedure_id),
                family=meta.family,
                state=state,
                cases=counts.get(procedure_id, 0),
                detail=detail,
            )
        )
    return out


def _blocked_by(failures: list[harness.CaseResult]) -> str:
    """The extras that would unblock these cases, as a phrase for the tile.

    Named from `errors.extra_for` rather than parsed out of the message, and
    from the *capability the row is missing in that language* rather than from
    the message's own wording. Several rows are blocked in two languages at
    once, so the extras are deduplicated and sorted — `requires denckring[de-
    wiktionary]` twice would say nothing the once does not.

    A capability nothing can supply — French `stress`, German
    `lexicon.graded_words` — has no extra to name, and says so instead of
    offering an install that would change nothing.
    """
    extras: set[str] = set()
    permanent = False
    for result in failures:
        meta = catalogue.get(result.procedure)
        for capability in runnable(meta, result.lang)[1]:
            extra = extra_for(result.lang, capability)
            if extra is None:
                permanent = True
            else:
                extras.add(extra)
    if extras:
        return "requires " + ", ".join(f"denckring[{name}]" for name in sorted(extras))
    return "no data distribution supplies this" if permanent else "requires data not installed"


def scoreboard_line() -> str:
    """The line `denckring status` prints, for the board to carry unchanged."""
    return harness.status().line()
