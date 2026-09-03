"""Serial lipogram — one part per letter, each omitting the letter it is given."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.errors import InvalidParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans, paragraph_spans, single_letter


class SerialLipogramParams(DiacriticParams):
    unit: Literal["paragraph", "line"] = Field(
        default="paragraph", description="What carries one letter's constraint."
    )
    start: str | None = Field(default=None, description="The letter the first part omits.")

    @field_validator("start")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("start must be a single alphabetic character")
        return value.lower()


@register
class SerialLipogram(BaseProcedure[SerialLipogramParams]):
    """The constraint walks the alphabet instead of holding to one letter.

    Where `abecedarian` can read its starting letter off the first line, this
    cannot: its constraint is an absence, and a short part is missing many
    letters. So the walk starts at the alphabet's first letter unless told
    otherwise — which is Tryphiodorus's own arrangement, book one omitting alpha.
    """

    id = "serial_lipogram"

    @classmethod
    def params_model(cls) -> type[SerialLipogramParams]:
        return SerialLipogramParams

    def _check(self, text: str, pack: LanguagePack, params: SerialLipogramParams) -> Report:
        alphabet = pack.alphabet()
        parts = paragraph_spans(text) if params.unit == "paragraph" else line_spans(text)
        # Folded before the alphabet-membership check, or `start="ä"` refused
        # outright even with folding on — stricter than the fold this row's
        # own comparison already performs against the text. ADR 0035, D3;
        # Known remaining.
        start = (
            None
            if params.start is None
            else single_letter(
                params.start,
                pack,
                fold=params.fold_diacritics,
                procedure_id=self.id,
                field="start",
            )
        )
        if start is not None and start not in alphabet:
            raise InvalidParams(
                self.id, f"start {start!r} is not a letter of the {pack.lang} alphabet"
            )
        first = alphabet.index(start) if start is not None else 0

        violations: list[Violation] = []
        good = 0
        for index, (offset, part) in enumerate(parts):
            forbidden = alphabet[(first + index) % len(alphabet)]
            hits = [
                span_offset
                for span_offset, ch in letter_spans(part, pack, fold=params.fold_diacritics)
                if ch == forbidden
            ]
            if hits:
                violations.append(
                    Violation(
                        rule="forbidden_letter",
                        offset=offset + hits[0],
                        found=forbidden,
                        expected=f"part {index + 1} without {forbidden!r}",
                    )
                )
            elif index < len(alphabet):
                # A part beyond the alphabet's length has no slot of its own —
                # `wrong_part_count` already marks the text unsatisfied, and
                # letting an extra correct part inflate `good` past `total`'s
                # alphabet-sized floor would let the score reach 1.0 anyway.
                good += 1

        if len(parts) != len(alphabet):
            violations.append(
                Violation(
                    rule="wrong_part_count",
                    offset=None,
                    found=f"{len(parts)} parts",
                    expected=f"{len(alphabet)} parts, one per letter of the alphabet",
                )
            )

        total = max(len(parts), len(alphabet))
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"parts": float(len(parts)), "expected_parts": float(len(alphabet))},
        )
