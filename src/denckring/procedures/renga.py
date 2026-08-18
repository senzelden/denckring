"""Renga — a linked chain of alternating three-line and two-line stanzas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import paragraph_spans
from denckring.procedures.syllable_count import line_syllables

HOKKU = [5, 7, 5]
WAKIKU = [7, 7]


class RengaParams(BaseModel):
    links: int | None = Field(
        default=None, description="How many stanzas to require. Unset means any number."
    )


@register
class Renga(BaseProcedure[RengaParams]):
    """Checks the alternation of 5-7-5 and 7-7 stanzas, and nothing else.

    That a renga is composed collaboratively, and that each link joins only to
    its neighbour rather than to the whole, are the definition's substance and
    neither is a property of the text. A solo renga whose links each answer the
    entire poem will still be reported satisfied.
    """

    id = "renga"

    @classmethod
    def params_model(cls) -> type[RengaParams]:
        return RengaParams

    def _check(self, text: str, pack: LanguagePack, params: RengaParams) -> Report:
        stanzas = paragraph_spans(text)
        violations: list[Violation] = []
        good = 0
        total = 0
        estimated = 0

        if len(stanzas) < 2:
            violations.append(
                Violation(
                    rule="too_few_links",
                    offset=None,
                    found=f"{len(stanzas)} stanzas",
                    expected="at least 2 — one stanza is a hokku, not a renga",
                )
            )
            total += 1

        if params.links is not None and len(stanzas) != params.links:
            violations.append(
                Violation(
                    rule="too_few_links",
                    offset=None,
                    found=f"{len(stanzas)} stanzas",
                    expected=f"{params.links} stanzas",
                )
            )
            total += 1

        for index, (offset, stanza) in enumerate(stanzas):
            wanted = HOKKU if index % 2 == 0 else WAKIKU
            measured = line_syllables(stanza, pack)
            estimated += sum(count for _, _, count in measured)
            total += 1
            if len(measured) != len(wanted):
                violations.append(
                    Violation(
                        rule="wrong_stanza_shape",
                        offset=offset,
                        found=f"{len(measured)} lines",
                        expected=f"{len(wanted)} lines",
                    )
                )
                continue
            faults = [
                Violation(
                    rule="wrong_syllable_count",
                    offset=line_offset,
                    found=f"{syllables} syllables",
                    expected=f"{expected} syllables",
                )
                for (line_offset, syllables, _), expected in zip(measured, wanted, strict=True)
                if syllables != expected
            ]
            violations += faults
            if not faults:
                good += 1

        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"stanzas": float(len(stanzas)), "estimated_words": float(estimated)},
        )
