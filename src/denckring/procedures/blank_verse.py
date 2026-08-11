"""Blank verse — Unrhymed iambic pentameter."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import rhyme_keys
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class BlankVerseParams(BaseModel):
    pass


@register
class BlankVerse(BaseProcedure[BlankVerseParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "blank_verse"

    @classmethod
    def params_model(cls) -> type[BlankVerseParams]:
        return BlankVerseParams

    def _check(self, text: str, pack: LanguagePack, params: BlankVerseParams) -> Report:
        violations, good, total = form_report(
            text,
            pack,
            metre="01" * 5,
        )

        # Blank verse is defined by the absence of rhyme, so any rhyming pair is
        # the violation — not merely adjacent ones, or ABAB would slip through.
        keys = rhyme_keys(text, pack)
        pairs = [(i, j) for i in range(len(keys)) for j in range(i + 1, len(keys))]
        for index, other in pairs:
            total += 1
            if keys[index][2] & keys[other][2]:
                violations.append(
                    Violation(
                        rule="unwanted_rhyme",
                        offset=keys[other][0],
                        found=keys[other][1],
                        expected=f"a word not rhyming with {keys[index][1]!r}",
                    )
                )
            else:
                good += 1

        return self._report(
            good=good, total=total, violations=violations, metrics={"checks": float(total)}
        )
