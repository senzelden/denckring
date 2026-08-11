"""Heterogram — no letter repeats."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class HeterogramParams(DiacriticParams):
    scope: Literal["text", "word"] = Field(default="text", description="Where repeats are banned.")


@register
class Heterogram(BaseProcedure[HeterogramParams]):
    """Borgmann's constraint: spend each letter once."""

    id = "heterogram"

    @classmethod
    def params_model(cls) -> type[HeterogramParams]:
        return HeterogramParams

    def _check(self, text: str, pack: LanguagePack, params: HeterogramParams) -> Report:
        groups: list[list[tuple[int, str]]]
        if params.scope == "text":
            groups = [letter_spans(text, pack, fold=params.fold_diacritics)]
        else:
            groups = [
                [
                    (offset + local, ch)
                    for local, ch in letter_spans(word, pack, fold=params.fold_diacritics)
                ]
                for offset, word in word_spans(text, pack)
            ]
        violations: list[Violation] = []
        total = 0
        for group in groups:
            seen: set[str] = set()
            for offset, ch in group:
                total += 1
                if ch in seen:
                    violations.append(
                        Violation(
                            rule="repeated_letter",
                            offset=offset,
                            found=ch,
                            expected="an unused letter",
                        )
                    )
                seen.add(ch)
        return self._report(
            good=total - len(violations),
            total=total,
            violations=violations,
            metrics={"letters": float(total), "repeats": float(len(violations))},
        )
