"""Reverse snowball — each word is one letter shorter than the last."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.snowball import rhopalic_violations


class ReverseSnowballParams(BaseModel):
    start: int | None = Field(
        default=None, description="Length of the first word; inferred if unset."
    )
    step: int = Field(default=-1, description="Letters removed per word.")


@register
class ReverseSnowball(BaseProcedure[ReverseSnowballParams]):
    """The melting snowball: the same walk as `snowball`, stepping down."""

    id = "reverse_snowball"

    @classmethod
    def params_model(cls) -> type[ReverseSnowballParams]:
        return ReverseSnowballParams

    def _check(self, text: str, pack: LanguagePack, params: ReverseSnowballParams) -> Report:
        violations, words = rhopalic_violations(text, pack, params.start, params.step)
        return self._report(
            good=words - len(violations),
            total=words,
            violations=violations,
            metrics={"words": float(words), "wrong": float(len(violations))},
        )
