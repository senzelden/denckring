"""S+7 — N+7 generalised to any displacement."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import Lang, LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.n_plus_7 import NPlus7Params, displace, displacement_report


class SPlus7Params(SourceParams):
    offset: int = Field(default=7, description="How many nouns to count forward.")


@register
class SPlus7(BaseProcedure[SPlus7Params]):
    """The same walk as N+7, with the step left to the writer."""

    id = "s_plus_7"

    @classmethod
    def params_model(cls) -> type[SPlus7Params]:
        return SPlus7Params

    def _check(self, text: str, pack: LanguagePack, params: SPlus7Params) -> Report:
        return displacement_report(
            self,  # type: ignore[arg-type]
            text,
            pack,
            NPlus7Params(source=params.source, offset=params.offset),
        )

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """The same walk, with the step the caller asked for."""
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        return displace(text, get_pack(lang), parsed.offset)
