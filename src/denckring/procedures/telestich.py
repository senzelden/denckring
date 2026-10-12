"""Telestich — the final letters of the units spell a target."""

from __future__ import annotations

from typing import ClassVar

from denckring.core.registry import register
from denckring.procedures.acrostic import Acrostic


@register
class Telestich(Acrostic):
    """The acrostic read from the other end of each line."""

    id = "telestich"
    rules = ("extra_unit", "missing_unit", "wrong_letter")

    # Inherits the acrostic checker whole, so a change to it moves this row too.
    composes = ("acrostic",)
    letter_index: ClassVar[int] = -1
