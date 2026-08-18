"""Univocalic translation — a translation into the target language restricted
throughout to a single vowel.

Only half of that is checkable. Whether the result honours the vowel constraint is
mechanical, and this row delegates that half whole to the already-registered
`univocalic` procedure, fetched via `denckring.core.registry.get` and called through
its own `check` — no new comparison lives here, and none should. Whether the result
*is a translation of* `params.source` is not decidable by this or any program: no
checker can tell that a univocalic rendering carries the sense of a given source
sentence, carries the sense of some other sentence, or carries no sense related to it
at all. That half is not attempted. Reading `describe_procedure("univocalic_translation")`
and concluding this row verifies translations would be a mistake this docstring exists
to head off — the row checks the constraint on the result, nothing more.

`apply` is deliberately not shipped (ADR 0002 makes it optional even though the
catalogue marks this row `kind: both`): producing a translation is invention, not a
mechanical transformation, so there is nothing here for a generator to do that would
not just be writing.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import get, register
from denckring.procedures.univocalic import UnivocalicParams


class UnivocalicTranslationParams(SourceParams, UnivocalicParams):
    pass


@register
class UnivocalicTranslation(BaseProcedure[UnivocalicTranslationParams]):
    """Checks only that the result is univocalic; whether it translates
    `params.source` is undecidable and unchecked."""

    id = "univocalic_translation"

    @classmethod
    def params_model(cls) -> type[UnivocalicTranslationParams]:
        return UnivocalicTranslationParams

    def _check(self, text: str, pack: LanguagePack, params: UnivocalicTranslationParams) -> Report:
        delegate = get("univocalic").check(
            text, lang=pack.lang, vowel=params.vowel, fold_diacritics=params.fold_diacritics
        )
        # `Report` exposes `score` and `violations`, not `good`/`total` directly.
        # `univocalic` counts one violation per foreign vowel occurrence, and its
        # score is exactly `good / total` whenever `total > 0` — so `total` is
        # recoverable from `score` and `bad = len(violations)` by solving
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
