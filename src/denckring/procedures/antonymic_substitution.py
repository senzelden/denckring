"""Antonymic substitution — one strict dictionary-backed step (ADR 0049)."""

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.relations import relation_report


@register
class AntonymicSubstitution(BaseProcedure[SourceParams]):
    id = "antonymic_substitution"

    @classmethod
    def params_model(cls) -> type[SourceParams]:
        return SourceParams

    def _check(self, text: str, pack: LanguagePack, params: SourceParams) -> Report:
        return relation_report(self, text, pack, params, "antonyms")
