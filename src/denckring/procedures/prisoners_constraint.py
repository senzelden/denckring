"""Prisoner's constraint — no letter with an ascender or a descender."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import clusters


class PrisonersConstraintParams(BaseModel):
    pass


@register
class PrisonersConstraint(BaseProcedure[PrisonersConstraintParams]):
    """The prisoner saving paper writes only within the x-height.

    The forbidden set is a property of the orthography's glyph shapes rather than
    of the language, which is why it comes from the pack's `letter_shapes`
    capability instead of being hard-coded here.
    """

    id = "prisoners_constraint"

    @classmethod
    def params_model(cls) -> type[PrisonersConstraintParams]:
        return PrisonersConstraintParams

    def _check(self, text: str, pack: LanguagePack, params: PrisonersConstraintParams) -> Report:
        # Clusters, not characters: a decomposed `ä` is `a` plus U+0308, and
        # taking those separately keeps the `a` — which is within the x-height —
        # and drops the mark that is not. `Bär` then scores better in NFD than in
        # NFC, which makes the verdict a fact about how the text was typed. This
        # is a glyph question, where folding is never right (ADR 0035).
        letters = [(offset, cluster) for offset, cluster in clusters(text) if cluster[0].isalpha()]
        violations = [
            Violation(
                rule="tall_or_deep_letter",
                offset=offset,
                found=ch,
                expected="a letter within the x-height",
            )
            for offset, ch in letters
            if pack.exceeds_x_height(ch)
        ]
        return self._report(
            good=len(letters) - len(violations),
            total=len(letters),
            violations=violations,
            metrics={"letters": float(len(letters)), "forbidden": float(len(violations))},
        )
