"""Letter bank — draw only on the letters of one source word, using each at least once."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class LetterBankParams(DiacriticParams):
    bank: str = Field(description="The source word supplying the permitted letters.")


@register
class LetterBank(BaseProcedure[LetterBankParams]):
    """Beau présent's stricter cousin: every bank letter must actually be spent."""

    id = "letter_bank"

    @classmethod
    def params_model(cls) -> type[LetterBankParams]:
        return LetterBankParams

    def _check(self, text: str, pack: LanguagePack, params: LetterBankParams) -> Report:
        fold = params.fold_diacritics
        allowed = {ch for _, ch in letter_spans(params.bank, pack, fold=fold)}
        letters = letter_spans(text, pack, fold=fold)
        violations = [
            Violation(
                rule="letter_outside_bank",
                offset=offset,
                found=ch,
                expected="".join(sorted(allowed)),
            )
            for offset, ch in letters
            if ch not in allowed
        ]
        outside = len(violations)
        unused = sorted(allowed - {ch for _, ch in letters})
        violations += [
            Violation(rule="unused_bank_letter", offset=None, found="", expected=ch)
            for ch in unused
        ]
        total = len(letters) + len(unused)
        return self._report(
            good=total - len(violations),
            total=total,
            violations=violations,
            metrics={
                "letters": float(len(letters)),
                "outside": float(outside),
                "unused": float(len(unused)),
            },
        )
