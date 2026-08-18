"""Lipogrammatic translation — a translation that observes a lipogram absent from
the original, or preserves one the original imposed (Gilbert Adair's *A Void*,
translating Perec's *La Disparition*).

Only half of that is checkable. Whether the result omits the forbidden letter is
mechanical, and this row delegates that half whole to the already-registered
`lipogram` procedure, fetched via `denckring.core.registry.get` and called through its
own `check` — no new comparison lives here, and none should. Whether the result *is a
translation of* `params.source` is not decidable by this or any program: no checker can
tell that an e-less rendering carries the sense of a given source sentence, carries the
sense of some other sentence, or carries no sense related to it at all. That half is
not attempted. Reading `describe_procedure("lipogrammatic_translation")` and concluding
this row verifies translations would be a mistake this docstring exists to head off —
the row checks the constraint on the result, nothing more.

`apply` is deliberately not shipped (ADR 0002 makes it optional even though the
catalogue marks this row `kind: both`): producing a translation is invention, not a
mechanical transformation, so there is nothing here for a generator to do that would
not just be writing.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import get, register
from denckring.procedures.lipogram import LipogramParams


class LipogrammaticTranslationParams(SourceParams, LipogramParams):
    pass


@register
class LipogrammaticTranslation(BaseProcedure[LipogrammaticTranslationParams]):
    """Checks only that the result is a lipogram; whether it translates
    `params.source` is undecidable and unchecked."""

    id = "lipogrammatic_translation"

    @classmethod
    def params_model(cls) -> type[LipogrammaticTranslationParams]:
        return LipogrammaticTranslationParams

    def _check(
        self, text: str, pack: LanguagePack, params: LipogrammaticTranslationParams
    ) -> Report:
        delegate = get("lipogram").check(
            text, lang=pack.lang, forbidden=params.forbidden, fold_diacritics=params.fold_diacritics
        )
        # `Report` exposes `score` and `violations`, not `good`/`total` directly.
        # `lipogram` counts one violation per occurrence of the forbidden letter,
        # and its score is exactly `good / total` whenever `total > 0` — so `total`
        # is recoverable from `score` and `bad = len(violations)` by solving
        # `total * (1 - score) == bad`. A score of 1.0 means zero violations;
        # good/total then collapse to 1/1, which is enough to keep `self._report`
        # vacuously satisfied without inventing a letter count that was never
        # exposed.
        bad = len(delegate.violations)
        if bad == 0:
            good, total = 1, 1
        else:
            total = round(bad / (1.0 - delegate.score))
            good = total - bad
        return self._report(
            good=good,
            total=total,
            violations=delegate.violations,
            metrics=dict(delegate.metrics),
        )
