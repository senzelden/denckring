"""Homoconsonantism — the consonants of the source, in order, with new vowels.

The first row of a new phase: procedures decidable only against the source text they
were made from. It was written by hand first, with the comparison inline and no
helper, precisely so that `denckring.core.source_compare.letter_class_report` would be
shaped by what this row and `homovocalism` actually share rather than by a guess made
before the second caller existed. See that module's docstring for what the hand-written
version taught.

`apply` is deliberately not shipped (ADR 0002 makes it optional even though the
catalogue marks this row `kind: both`): choosing new vowels around a fixed consonant
skeleton to make a new sense is invention, not a mechanical transformation, so there is
nothing here for a generator to do that would not just be writing.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.source_compare import letter_class_report


class HomoconsonantismParams(SourceParams, DiacriticParams):
    pass


@register
class Homoconsonantism(BaseProcedure[HomoconsonantismParams]):
    """The consonant skeleton is the constraint; the vowels are the freedom."""

    id = "homoconsonantism"

    @classmethod
    def params_model(cls) -> type[HomoconsonantismParams]:
        return HomoconsonantismParams

    def _check(self, text: str, pack: LanguagePack, params: HomoconsonantismParams) -> Report:
        result = letter_class_report(
            text, params.source, pack, keep="consonants", fold=params.fold_diacritics
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"kept": float(result.total)},
        )
