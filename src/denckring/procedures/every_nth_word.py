"""Every nth word — keep one word in n and discard the rest."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans

MIN_STEP = 1


class EveryNthWordParams(SourceParams):
    n: int = Field(default=7, ge=MIN_STEP, description="Keep one word in every n.")


@register
class EveryNthWord(BaseProcedure[EveryNthWordParams]):
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

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Produce the selection from `text`, which serves as the source."""
        from denckring.lang import get_pack

        parsed = self.params_model().model_validate({"source": text, **params})
        return " ".join(self._select(text, get_pack(lang), parsed.n))
