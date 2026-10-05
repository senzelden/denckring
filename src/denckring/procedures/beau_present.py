"""Beau présent — a text using only the letters of a dedicatee's name."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.scope import Scope
from denckring.core.text import letter_spans


class BeauPresentParams(DiacriticParams):
    name: str = Field(
        description="The dedicatee's name, whose letters are the alphabet.",
        json_schema_extra=param("task", "name"),
    )
    require_all: bool = Field(
        default=False,
        description="Every name letter must appear.",
        json_schema_extra=param("switch"),
    )


@register
class BeauPresent(BaseProcedure[BeauPresentParams]):
    """Perec's dedication form: the name supplies the whole alphabet."""

    id = "beau_present"
    rules = ("letter_outside_name", "unused_name_letter")
    local_scope = "word"

    @classmethod
    def params_model(cls) -> type[BeauPresentParams]:
        return BeauPresentParams

    def scope(self, params: BeauPresentParams) -> Scope:
        """`require_all` asks the text as a whole to use every name letter."""
        return "text" if params.require_all else "word"

    def _check(self, text: str, pack: LanguagePack, params: BeauPresentParams) -> Report:
        allowed = {ch for _, ch in letter_spans(params.name, pack, fold=params.fold_diacritics)}
        letters = letter_spans(text, pack, fold=params.fold_diacritics)
        violations = [
            Violation(
                rule="letter_outside_name",
                offset=offset,
                found=ch,
                expected="".join(sorted(allowed)),
            )
            for offset, ch in letters
            if ch not in allowed
        ]
        outside = len(violations)
        used = {ch for _, ch in letters}
        unused = sorted(allowed - used) if params.require_all else []
        violations += [
            Violation(rule="unused_name_letter", offset=None, found="", expected=ch)
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
                "unused_name_letters": float(len(unused)),
            },
        )
