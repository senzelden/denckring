"""Sestina — the quenina at six end-words."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.quenina import Quenina, QueninaParams

SESTINA_SIZE = 6


class SestinaParams(BaseModel):
    pass


@register
class Sestina(BaseProcedure[SestinaParams]):
    """Six sestets on six rotating end-words, checked as a quenina at n=6."""

    id = "sestina"

    @classmethod
    def params_model(cls) -> type[SestinaParams]:
        return SestinaParams

    def _check(self, text: str, pack: LanguagePack, params: SestinaParams) -> Report:
        report = Quenina()._check(text, pack, QueninaParams(n=SESTINA_SIZE))
        return report.model_copy(update={"procedure": self.id})
