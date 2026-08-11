"""Tanka — Five lines of five, seven, five, seven and seven syllables."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import pattern_result

PATTERN = [5, 7, 5, 7, 7]


class TankaParams(BaseModel):
    pass


@register
class Tanka(BaseProcedure[TankaParams]):
    """Checks the syllable pattern only; subject and season are not code's business."""

    id = "tanka"

    @classmethod
    def params_model(cls) -> type[TankaParams]:
        return TankaParams

    def _check(self, text: str, pack: LanguagePack, params: TankaParams) -> Report:
        return self._report(**pattern_result(text, pack, PATTERN)._asdict())
