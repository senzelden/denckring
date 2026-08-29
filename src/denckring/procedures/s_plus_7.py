"""S+7 — N+7 generalised to any displacement."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.protocol import LanguagePack, Produced, Report
from denckring.core.registry import register
from denckring.procedures.n_plus_7 import NPlus7Params, displace, displacement_report


class SPlus7Params(SourceParams):
    offset: int = Field(default=7, description="How many nouns to count forward.")


class SPlus7ApplyParams(SPlus7Params, ApplyParams):
    pass


@register
class SPlus7(ConstructiveProcedure[SPlus7Params, SPlus7ApplyParams]):
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

    @classmethod
    def apply_params_model(cls) -> type[SPlus7ApplyParams]:
        return SPlus7ApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: SPlus7ApplyParams) -> Produced:
        """The same walk, with the step the caller asked for."""
        return plain([displace(text, pack, params.offset)])
