"""Shakespearean sonnet — Three quatrains and a couplet in iambic pentameter."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class ShakespeareanSonnetParams(BaseModel):
    pass


@register
class ShakespeareanSonnet(BaseProcedure[ShakespeareanSonnetParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "shakespearean_sonnet"

    @classmethod
    def params_model(cls) -> type[ShakespeareanSonnetParams]:
        return ShakespeareanSonnetParams

    def _check(self, text: str, pack: LanguagePack, params: ShakespeareanSonnetParams) -> Report:
        violations, good, total = form_report(
            text,
            pack,
            scheme="ABABCDCDEFEFGG",
            metre="01" * 5,
        )

        return self._report(
            good=good, total=total, violations=violations, metrics={"checks": float(total)}
        )
