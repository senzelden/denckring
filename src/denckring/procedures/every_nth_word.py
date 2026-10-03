"""Every nth word — keep one word in n and discard the rest."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
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
    rules = ("extra_words", "wrong_word")

    @classmethod
    def params_model(cls) -> type[EveryNthWordParams]:
        return EveryNthWordParams

    def _check(self, text: str, pack: LanguagePack, params: EveryNthWordParams) -> Report:
        expected = self._select(params.source, pack, params.n)
        spans = word_spans(text, pack)
        actual = [word.casefold() for _, word in spans]
        violations: list[Violation] = []
        matched = 0
        for index, word in enumerate(expected):
            if index < len(actual) and actual[index] == word:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_word",
                        # Placed at the text's word, as `positional_report`
                        # places its siblings'; a word the text runs out before
                        # goes at the text's end, where it would go
                        # (`Violation.offset`).
                        offset=spans[index][0] if index < len(spans) else len(text),
                        found=actual[index] if index < len(actual) else "",
                        expected=word,
                    )
                )
        if len(actual) > len(expected):
            violations.append(
                Violation(
                    rule="extra_words",
                    offset=spans[len(expected)][0],
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

    def _produce(self, text: str, pack: LanguagePack, params: EveryNthWordApplyParams) -> Produced:
        """Produce the selection from `text`, which serves as the source."""
        return plain([" ".join(self._select(text, pack, params.n))])
