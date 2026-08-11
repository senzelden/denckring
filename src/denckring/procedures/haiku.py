"""Haiku — Three lines of five, seven and five syllables."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import pattern_result

PATTERN = [5, 7, 5]


class HaikuParams(BaseModel):
    pass


@register
class Haiku(BaseProcedure[HaikuParams]):
    """Checks the syllable pattern only; subject and season are not code's business."""

    id = "haiku"

    @classmethod
    def params_model(cls) -> type[HaikuParams]:
        return HaikuParams

    def _check(self, text: str, pack: LanguagePack, params: HaikuParams) -> Report:
        return self._report(**pattern_result(text, pack, PATTERN)._asdict())
