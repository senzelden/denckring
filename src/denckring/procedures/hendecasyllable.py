"""Hendecasyllable — Every line of exactly eleven syllables."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import line_syllables, pattern_result

SYLLABLES_PER_LINE = 11


class HendecasyllableParams(BaseModel):
    pass


@register
class Hendecasyllable(BaseProcedure[HendecasyllableParams]):
    """Checks the syllable measure only, not the caesura or the stress pattern."""

    id = "hendecasyllable"

    @classmethod
    def params_model(cls) -> type[HendecasyllableParams]:
        return HendecasyllableParams

    def _check(self, text: str, pack: LanguagePack, params: HendecasyllableParams) -> Report:
        lines = len(line_syllables(text, pack))
        result = pattern_result(text, pack, [SYLLABLES_PER_LINE] * lines)
        return self._report(**result._asdict())
