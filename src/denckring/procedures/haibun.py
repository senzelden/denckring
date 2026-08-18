"""Haibun — prose and haiku alternating in one work."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import paragraph_spans
from denckring.procedures.syllable_count import line_syllables

HAIKU = [5, 7, 5]


def _is_haiku(block: str, pack: LanguagePack) -> bool:
    measured = line_syllables(block, pack)
    return len(measured) == len(HAIKU) and all(
        syllables == expected for (_, syllables, _), expected in zip(measured, HAIKU, strict=True)
    )


class HaibunParams(BaseModel):
    pass


@register
class Haibun(BaseProcedure[HaibunParams]):
    """Checks the alternation of prose and 5-7-5 verse only.

    Whether the haiku condenses the passage rather than continuing it is a
    judgement about sense, which no checker can make. It is not checked, and a
    haibun that fails it will still be reported satisfied.
    """

    id = "haibun"

    @classmethod
    def params_model(cls) -> type[HaibunParams]:
        return HaibunParams

    def _check(self, text: str, pack: LanguagePack, params: HaibunParams) -> Report:
        blocks = paragraph_spans(text)
        kinds = [(offset, _is_haiku(block, pack)) for offset, block in blocks]
        violations: list[Violation] = []
        total = 2
        good = 0

        if not any(verse for _, verse in kinds):
            violations.append(
                Violation(
                    rule="missing_haiku",
                    offset=None,
                    found=f"{len(blocks)} blocks, none a 5-7-5 verse",
                    expected="at least one haiku",
                )
            )
        else:
            good += 1

        if not any(not verse for _, verse in kinds):
            violations.append(
                Violation(
                    rule="missing_prose",
                    offset=None,
                    found=f"{len(blocks)} blocks, all verse",
                    expected="at least one prose passage",
                )
            )
        else:
            good += 1

        for index, (offset, verse) in enumerate(kinds):
            total += 1
            if verse == bool(index % 2):
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_alternation",
                        offset=offset,
                        found="verse" if verse else "prose",
                        expected="prose" if index % 2 == 0 else "verse",
                    )
                )

        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"blocks": float(len(blocks)), "estimated_words": 0.0},
        )
