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
    #: True: every numeral letter counts, and capitals mark nothing. Hilton calls a line
    #: that reaches its date only by counting initials "a very bad one" for its
    #: "superfluous numeral letters" (*Chronograms*, 1882, p. 9), and faults careless
    #: makers for "little regard being paid to the necessity of avoiding superfluous
    #: letters" (p. 87).
    every_occurrence: bool
    case_sensitive: bool
    #: The parameter that decides whether accented letters count as their base letter.
    folds: str
    skipped: str
