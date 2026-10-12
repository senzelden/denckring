"""How a row that totals letter values counts them (ADR 0061 D4).

A module of its own because `core.base` must name `Counting` as a class attribute
and `core.describe` imports `core.base`: defining it in `describe` would be a cycle.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Counting(BaseModel):
    """How a row that totals letter values counts them (ADR 0061 D4)."""

    values: dict[str, int]
    combine: Literal["sum"]
    #: False: `IV` totals 6, not 4. Chronograms are additive.
    subtractive: bool
    #: True: no numeral letter may be "passed over to suit the convenience of the
    #: composer" (Hilton, *Chronograms*, 1882, p. 9). Capitals mark nothing.
    every_occurrence: bool
    case_sensitive: bool
    #: The parameter that decides whether accented letters count as their base letter.
    folds: str
    skipped: str
