"""How a row that totals letter values counts them (ADR 0061 D4).

A module of its own because `core.base` must name `Counting` as a class attribute
and `core.describe` imports `core.base`: defining it in `describe` would be a cycle.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Counting(BaseModel):
    """How a row that totals letter values counts them (ADR 0061 D4)."""

    # Frozen because the row holds one instance as a class attribute; `describe` hands
    # out a deep copy, so a caller editing `values` cannot change what the next one reads.
    model_config = ConfigDict(frozen=True)

    values: dict[str, int]
    combine: Literal["sum"]
    #: False: `IV` totals 6, not 4. Chronograms are additive.
    subtractive: bool
    #: True: every numeral letter counts; no occurrence is passed over as superfluous.
    #: Hilton calls a line that reaches its date only by counting initials "a very bad
    #: one" for its "superfluous numeral letters" (*Chronograms*, 1882, p. 9), and faults
    #: careless makers for "little regard being paid to the necessity of avoiding
    #: superfluous letters" (p. 87).
    every_occurrence: bool
    #: Whether case decides what counts by default: False, capitals mark nothing.
    case_sensitive: bool
    #: The parameter that, when set, makes case decide: only numeral letters written as
    #: capitals count (ADR 0064). `None` when no parameter can. Optional with a default
    #: because `Counting` is promised (ADR 0060): a consumer parsing a 0.5.0 `Counting`
    #: still validates.
    case_switch: str | None = None
    #: The parameter that decides whether accented letters count as their base letter.
    folds: str
    skipped: str
