"""Every nth word — keep one word in n and discard the rest."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans

MIN_STEP = 1


class EveryNthWordParams(SourceParams):
    n: int = Field(default=7, ge=MIN_STEP, description="Keep one word in every n.")


class EveryNthWordApplyParams(EveryNthWordParams, ApplyParams):
    pass


@register
class EveryNthWord(ConstructiveProcedure[EveryNthWordParams, EveryNthWordApplyParams]):
    """Constructive: `apply` performs the selection `check` verifies."""

    id = "every_nth_word"

    @classmethod
    def params_model(cls) -> type[EveryNthWordParams]:
        return EveryNthWordParams

    def _check(self, text: str, pack: LanguagePack, params: EveryNthWordParams) -> Report:
        expected = self._select(params.source, pack, params.n)
        actual = [word.casefold() for _, word in word_spans(text, pack)]
        violations: list[Violation] = []
        matched = 0
        for index, word in enumerate(expected):
            if index < len(actual) and actual[index] == word:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_word",
                        offset=None,
                        found=actual[index] if index < len(actual) else "",
                        expected=word,
                    )
                )
        if len(actual) > len(expected):
            violations.append(
                Violation(
                    rule="extra_words",
                    offset=None,
                    found=" ".join(actual[len(expected) :]),
                    expected="",
                )
            )
        return self._report(
            good=matched,
            total=max(len(expected), len(actual)),
            violations=violations,
            metrics={"kept": float(len(expected))},
        )

    @staticmethod
    def _select(source: str, pack: LanguagePack, n: int) -> list[str]:
        words = [word.casefold() for _, word in word_spans(source, pack)]
        return words[n - 1 :: n]

    @classmethod
    def apply_params_model(cls) -> type[EveryNthWordApplyParams]:
        return EveryNthWordApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: EveryNthWordApplyParams) -> list[str]:
        """Produce the selection from `text`, which serves as the source."""
        return [" ".join(self._select(text, pack, params.n))]
