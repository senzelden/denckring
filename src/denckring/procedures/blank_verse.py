"""Blank verse — Unrhymed iambic pentameter."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, MetreParams, RhymeParams
from denckring.core.prosody import must_rhyme, rhyme_evidence, rhyme_keys
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class BlankVerseParams(RhymeParams, MetreParams):
    pass


@register
class BlankVerse(BaseProcedure[BlankVerseParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "blank_verse"
    rules = ("unknown_rhyme", "unwanted_rhyme", "wrong_line_length", "wrong_stress")

    @classmethod
    def params_model(cls) -> type[BlankVerseParams]:
        return BlankVerseParams

    def _check(self, text: str, pack: LanguagePack, params: BlankVerseParams) -> Report:
        result = form_report(
            text,
            pack,
            metre="01" * 5,
            feminine_ending=params.feminine_ending,
        )
        violations = result.violations
        good = result.good
        total = result.total

        # Blank verse is defined by the absence of rhyme, so any rhyming pair is
        # the violation — not merely adjacent ones, or ABAB would slip through.
        keys = rhyme_keys(text, pack)
        pairs = [(i, j) for i in range(len(keys)) for j in range(i + 1, len(keys))]
        for index, other in pairs:
            total += 1
            unknown = [keys[i][1] for i in (other, index) if not keys[i][3]]
            # Only `strict` reads an ending the dictionary lacks: an unknown key set
            # rhymes with nothing, so it has always counted as unrhymed, and both
            # other settings keep that reading, which keeps the default verdict.
            if unknown and params.unknown_rhyme == "strict":
                violations.append(
                    Violation(
                        rule="unknown_rhyme",
                        offset=keys[other][0],
                        found=unknown[0],
                        expected="a word the pronouncing dictionary carries",
                    )
                )
            # Only a pair no choice of readings keeps apart rhymes against the
            # form (ADR 0057), as `scheme_violations` reads an unwanted rhyme.
            elif must_rhyme(keys[index][2], keys[other][2]):
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
            good=good,
            total=total,
            violations=violations,
            metrics={"checks": float(total), "estimated_words": float(result.estimated)},
            # The metre scan's account, plus the line endings the no-rhyme rule
            # was decided on — both are measurements this verdict rests upon.
            evidence=list(result.evidence) + list(rhyme_evidence(keys)),
        )
