"""Belle absente — one line per letter of a name, each line without that letter."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans


class BelleAbsenteParams(DiacriticParams):
    name: str = Field(description="The dedicatee. One line per letter of it.")

    @field_validator("name")
    @classmethod
    def _has_letters(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("name must contain at least one letter")
        return value


@register
class BelleAbsente(BaseProcedure[BelleAbsenteParams]):
    """Perec's form: the absent letter spells the dedication.

    Each line omits one letter of the name and uses every other letter of the
    alphabet, so the missing letters read down the poem as the name itself.
    """

    id = "belle_absente"

    @classmethod
    def params_model(cls) -> type[BelleAbsenteParams]:
        return BelleAbsenteParams

    def _check(self, text: str, pack: LanguagePack, params: BelleAbsenteParams) -> Report:
        alphabet = pack.alphabet()
        # The space in "Georges Perec" is not a constraint, and neither is a
        # hyphen: the name reduces to the letters it is spelled with.
        wanted = [ch for ch in params.name.lower() if ch.isalpha()]
        lines = line_spans(text)

        violations: list[Violation] = []
        good = 0
        for index, letter in enumerate(wanted):
            if index >= len(lines):
                continue
            offset, line = lines[index]
            present = {ch for _, ch in letter_spans(line, pack, fold=params.fold_diacritics)}
            intruder = [
                span_offset
                for span_offset, ch in letter_spans(line, pack, fold=params.fold_diacritics)
                if ch == letter
            ]
            missing = [ch for ch in alphabet if ch != letter and ch not in present]
            if intruder:
                violations.append(
                    Violation(
                        rule="forbidden_letter_present",
                        offset=intruder[0],
                        found=letter,
                        expected=f"line {index + 1} without {letter!r}",
                    )
                )
            for ch in missing:
                violations.append(
                    Violation(
                        rule="missing_letter",
                        offset=offset,
                        found="",
                        expected=f"{ch!r} somewhere in line {index + 1}",
                    )
                )
            if not intruder and not missing:
                good += 1

        if len(lines) != len(wanted):
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{len(wanted)} lines, one per letter of the name",
                )
            )
        return self._report(
            good=good,
            total=max(len(wanted), len(lines)),
            violations=violations,
            metrics={"lines": float(len(lines)), "letters": float(len(wanted))},
        )
