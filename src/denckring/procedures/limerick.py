"""Limerick — Five lines rhyming AABBA."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class LimerickParams(BaseModel):
    pass


@register
class Limerick(BaseProcedure[LimerickParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "limerick"

    @classmethod
    def params_model(cls) -> type[LimerickParams]:
        return LimerickParams

    def _check(self, text: str, pack: LanguagePack, params: LimerickParams) -> Report:
        violations, good, total = form_report(
            text,
            pack,
            scheme="AABBA",
        )

        return self._report(
            good=good, total=total, violations=violations, metrics={"checks": float(total)}
        )
