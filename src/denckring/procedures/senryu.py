"""Senryu — A haiku's measure turned on human folly rather than nature."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import pattern_result

PATTERN = [5, 7, 5]


class SenryuParams(BaseModel):
    pass


@register
class Senryu(BaseProcedure[SenryuParams]):
    """Checks the syllable pattern only; subject and season are not code's business."""

    id = "senryu"

    @classmethod
    def params_model(cls) -> type[SenryuParams]:
        return SenryuParams

    def _check(self, text: str, pack: LanguagePack, params: SenryuParams) -> Report:
        return self._report(**pattern_result(text, pack, PATTERN)._asdict())
