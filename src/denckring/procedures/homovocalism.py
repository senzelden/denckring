"""Homovocalism — the mirror of homoconsonantism: the vowels are kept, in order.

Built directly on `denckring.core.source_compare.letter_class_report`, extracted from
`homoconsonantism` once this row existed to need it — see that module's docstring for
why the extraction waited.

`apply` is deliberately not shipped (ADR 0002 makes it optional even though the
catalogue marks this row `kind: both`): choosing new consonants around a fixed vowel
sequence to make a new sense is invention, not a mechanical transformation, so there is
nothing here for a generator to do that would not just be writing.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.source_compare import letter_class_report


class HomovocalismParams(SourceParams, DiacriticParams):
    pass


@register
class Homovocalism(BaseProcedure[HomovocalismParams]):
    """The vowel sequence is the constraint; the consonants are the freedom."""

    id = "homovocalism"

    @classmethod
    def params_model(cls) -> type[HomovocalismParams]:
        return HomovocalismParams

    def _check(self, text: str, pack: LanguagePack, params: HomovocalismParams) -> Report:
        result = letter_class_report(
            text, params.source, pack, keep="vowels", fold=params.fold_diacritics
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"kept": float(result.total)},
        )
