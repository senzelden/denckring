"""Telestich — the final letters of the units spell a target."""

from __future__ import annotations

from typing import ClassVar

from denckring.core.registry import register
from denckring.procedures.acrostic import Acrostic


@register
class Telestich(Acrostic):
    """The acrostic read from the other end of each line."""

    id = "telestich"

    letter_index: ClassVar[int] = -1
