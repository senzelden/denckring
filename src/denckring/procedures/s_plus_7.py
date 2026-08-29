"""S+7 — N+7 generalised to any displacement."""

from __future__ import annotations

from denckring.core.base import ApplyParams, ConstructiveProcedure, plain
from denckring.core.protocol import LanguagePack, Produced, Report
from denckring.core.registry import register
from denckring.procedures.n_plus_7 import (
    NPlus7Params,
    displace,
    displacement_report,
    resolve_dictionary,
)


class SPlus7Params(NPlus7Params):
    """N+7's fields — `offset`, `dictionary`, `ambiguous_nouns` — with the step left to the writer.

    Inherits rather than duplicates: a second `offset` field here, kept in sync
    by hand, is exactly how `dictionary` would have stayed n_plus_7-only despite
    this module already delegating to `NPlus7Params` and `displacement_report`.
    """


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
        # `params` already is an `NPlus7Params` — `SPlus7Params` adds no fields
        # of its own — so this is a pass-through, not a reconstruction.
        return displacement_report(self, text, pack, params)  # type: ignore[arg-type]

    @classmethod
    def apply_params_model(cls) -> type[SPlus7ApplyParams]:
        return SPlus7ApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: SPlus7ApplyParams) -> Produced:
        """The same walk, with the step the caller asked for."""
        nouns, noun_index = resolve_dictionary(pack, params.dictionary)
        return plain([displace(text, pack, nouns, noun_index, params.offset)])
