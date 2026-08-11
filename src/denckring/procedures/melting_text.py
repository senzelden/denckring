"""Melting text — the source with words dropped, the order kept."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class MeltingTextParams(SourceParams):
    pass


@register
class MeltingText(BaseProcedure[MeltingTextParams]):
    """Each stage keeps a subsequence of the source and adds nothing."""

    id = "melting_text"

    @classmethod
    def params_model(cls) -> type[MeltingTextParams]:
        return MeltingTextParams

    def _check(self, text: str, pack: LanguagePack, params: MeltingTextParams) -> Report:
        candidate = word_spans(text, pack)
        source = [word.casefold() for _, word in word_spans(params.source, pack)]
        violations: list[Violation] = []
        matched = 0
        cursor = 0
        for offset, word in candidate:
            folded = word.casefold()
            try:
                cursor = source.index(folded, cursor) + 1
            except ValueError:
                violations.append(
                    Violation(
                        rule="word_not_in_source",
                        offset=offset,
                        found=word,
                        expected="a word remaining in the source, in order",
                    )
                )
            else:
                matched += 1
        return self._report(
            good=matched,
            total=len(candidate),
            violations=violations,
            metrics={"kept": float(matched), "source_words": float(len(source))},
        )
