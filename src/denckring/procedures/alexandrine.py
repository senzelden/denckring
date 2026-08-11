"""Alexandrine — Every line of exactly twelve syllables."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import line_syllables, pattern_result

SYLLABLES_PER_LINE = 12


class AlexandrineParams(BaseModel):
    pass


@register
class Alexandrine(BaseProcedure[AlexandrineParams]):
    """Checks the syllable measure only, not the caesura or the stress pattern."""

    id = "alexandrine"

    @classmethod
    def params_model(cls) -> type[AlexandrineParams]:
        return AlexandrineParams

    def _check(self, text: str, pack: LanguagePack, params: AlexandrineParams) -> Report:
        lines = len(line_syllables(text, pack))
        result = pattern_result(text, pack, [SYLLABLES_PER_LINE] * lines)
        return self._report(**result._asdict())
