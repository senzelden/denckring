"""Cinquain — Five lines of two, four, six, eight and two syllables."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import pattern_result

PATTERN = [2, 4, 6, 8, 2]


class CinquainParams(BaseModel):
    pass


@register
class Cinquain(BaseProcedure[CinquainParams]):
    """Checks the syllable pattern only; subject and season are not code's business."""

    id = "cinquain"

    @classmethod
    def params_model(cls) -> type[CinquainParams]:
        return CinquainParams

    def _check(self, text: str, pack: LanguagePack, params: CinquainParams) -> Report:
        return self._report(**pattern_result(text, pack, PATTERN)._asdict())
