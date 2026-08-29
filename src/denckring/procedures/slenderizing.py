"""Slenderizing — the source with every instance of one letter deleted."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import (
    ApplyParams,
    ConstructiveProcedure,
    DiacriticParams,
    SourceParams,
    plain,
)
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class SlenderizingParams(SourceParams, DiacriticParams):
    deleted: str = Field(description="The letter removed from the source.")

    @field_validator("deleted")
    @classmethod
    def _single_letter(cls, value: str) -> str:
        if len(value) != 1 or not value.isalpha():
            raise ValueError("deleted must be a single alphabetic character")
        return value.lower()


class SlenderizingApplyParams(SlenderizingParams, ApplyParams):
    pass


@register
class Slenderizing(ConstructiveProcedure[SlenderizingParams, SlenderizingApplyParams]):
    """Strike out one letter throughout and let the rest close up."""

    id = "slenderizing"

    @classmethod
    def params_model(cls) -> type[SlenderizingParams]:
        return SlenderizingParams

    def _check(self, text: str, pack: LanguagePack, params: SlenderizingParams) -> Report:
        fold = params.fold_diacritics
        expected = [
            ch for _, ch in letter_spans(params.source, pack, fold=fold) if ch != params.deleted
        ]
        actual = [ch for _, ch in letter_spans(text, pack, fold=fold)]
        violations: list[Violation] = []
        matched = 0
        for index, letter in enumerate(expected):
            if index < len(actual) and actual[index] == letter:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_letter",
                        offset=None,
                        found=actual[index] if index < len(actual) else "",
                        expected=letter,
                    )
                )
        if len(actual) > len(expected):
            violations.append(
                Violation(
                    rule="extra_letters",
                    offset=None,
                    found="".join(actual[len(expected) :]),
                    expected="",
                )
            )
        return self._report(
            good=matched,
            total=max(len(expected), len(actual)),
            violations=violations,
            metrics={"expected": float(len(expected)), "actual": float(len(actual))},
        )

    @classmethod
    def apply_params_model(cls) -> type[SlenderizingApplyParams]:
        return SlenderizingApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: SlenderizingApplyParams) -> Produced:
        """Strike the letter out of `text` and let the rest close up.

        No seed: there is exactly one slenderizing of a text for a given letter,
        which is why this generator takes no choices at all.
        """
        return plain(
            [
                "".join(
                    ch
                    for ch in text
                    if not ch.isalpha() or pack.fold_diacritics(ch).lower() != params.deleted
                )
            ]
        )
