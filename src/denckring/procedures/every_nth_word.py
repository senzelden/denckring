"""Every nth word — keep one word in n and discard the rest."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Produced, Report
from denckring.core.registry import register
from denckring.core.source_compare import aligned_report
from denckring.core.text import word_spans

MIN_STEP = 1


class EveryNthWordParams(SourceParams):
    n: int = Field(
        default=7,
        ge=MIN_STEP,
        description="Keep one word in every n.",
        json_schema_extra=param("task"),
    )


class EveryNthWordApplyParams(EveryNthWordParams, ApplyParams):
    pass


@register
class EveryNthWord(ConstructiveProcedure[EveryNthWordParams, EveryNthWordApplyParams]):
    """Constructive: `apply` performs the selection `check` verifies."""

    id = "every_nth_word"
    rules = ("extra_words", "missing_word", "wrong_word")

    @classmethod
    def params_model(cls) -> type[EveryNthWordParams]:
        return EveryNthWordParams

    def _check(self, text: str, pack: LanguagePack, params: EveryNthWordParams) -> Report:
        expected = self._select(params.source, pack, params.n)
        spans = word_spans(text, pack)
        # Aligned (ADR 0056): a dropped word costs one unit, not every word after
        # it. Placed at the text's word, as `positional_report` places its
        # siblings'; a missing word no later word follows goes at the text's end,
        # where it would go (`Violation.offset`).
        result = aligned_report(
            expected,
            [(offset, word.casefold()) for offset, word in spans],
            key=lambda word: word,
            substituted="wrong_word",
            inserted="extra_words",
            deleted="missing_word",
            joiner=" ",
            end=len(text),
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"kept": float(len(expected))},
        )

    @staticmethod
    def _select(source: str, pack: LanguagePack, n: int) -> list[str]:
        words = [word.casefold() for _, word in word_spans(source, pack)]
        return words[n - 1 :: n]

    @classmethod
    def apply_params_model(cls) -> type[EveryNthWordApplyParams]:
        return EveryNthWordApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: EveryNthWordApplyParams) -> Produced:
        """Produce the selection from `text`, which serves as the source."""
        return plain([" ".join(self._select(text, pack, params.n))])
