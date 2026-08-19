"""Ballade — three ababbcbc stanzas and a bcbc envoi, every part ending on the refrain.

The refrain is the form's point: the same line closes all four parts, at indices
7, 15, 23 and 27 — all four sharing the scheme's final letter, "c". A strict scheme
check (`allow_identical=False`) would flag every one of the six pairs among those
four lines as `identical_rhyme`, even though the identical text is exactly what
the refrain requires. Only those refrain-to-refrain pairs are exempt; any other
same-letter line that happens to repeat a word — including a line that is not a
refrain position but copies the refrain's word — stays flagged.

The exemption is counted independently via `rhyme_keys` rather than read off the
`Violation` objects `scheme_violations` returns: a violation's `offset` names only
the later line of its pair, not the earlier one, so there is no way to tell from a
single violation whether the earlier line was genuinely a refrain line or some
other line that happens to share its word. Counting the legitimate refrain-refrain
pairs independently and dropping that many matching `identical_rhyme` violations
per offset sidesteps the ambiguity: any violation left over at a refrain's offset
is a genuine duplicate outside the refrain, not a refrain pair, and stays reported.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import repeat_to, rhyme_keys, scheme_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ababbcbc" * 3 + "bcbc"
LINES = 28
#: The refrain closes stanza one at index 7, and must return at 15, 23 and 27.
REFRAINS = [(7, 15), (7, 23), (7, 27)]
REFRAIN_INDICES = sorted({index for pair in REFRAINS for index in pair})

RhymeKeys = list[tuple[int, str, frozenset[str], bool]]


def _exempt_refrain_identicals(
    violations: list[Violation], keys: RhymeKeys
) -> tuple[list[Violation], int]:
    """Drop one `identical_rhyme` violation per genuine refrain-to-refrain pair.

    `to_drop` counts, per line offset, how many of that line's identical_rhyme
    violations are legitimately exempt — computed straight from `rhyme_keys`,
    not from the violations themselves. A violation matching that offset is
    dropped only while its count remains; once used up, any further violation
    at that offset (a duplicate the refrain does not explain) stays reported.
    """
    to_drop: dict[int, int] = {}
    for a in range(len(REFRAIN_INDICES)):
        for b in range(a + 1, len(REFRAIN_INDICES)):
            i, j = REFRAIN_INDICES[a], REFRAIN_INDICES[b]
            if keys[i][1].casefold() == keys[j][1].casefold():
                refrain_offset = keys[j][0]
                to_drop[refrain_offset] = to_drop.get(refrain_offset, 0) + 1

    kept: list[Violation] = []
    exempted = 0
    for violation in violations:
        offset = violation.offset
        remaining = to_drop.get(offset, 0) if offset is not None else 0
        if violation.rule == "identical_rhyme" and offset is not None and remaining > 0:
            to_drop[offset] = remaining - 1
            exempted += 1
        else:
            kept.append(violation)
    return kept, exempted


class BalladeParams(RhymeParams):
    pass


@register
class Ballade(BaseProcedure[BalladeParams]):
    """Twenty-eight lines, four of them the same line."""

    id = "ballade"

    @classmethod
    def params_model(cls) -> type[BalladeParams]:
        return BalladeParams

    def _check(self, text: str, pack: LanguagePack, params: BalladeParams) -> Report:
        result = form_report(
            text,
            pack,
            metre=repeat_to("01", 4),
            refrains=REFRAINS,
            lines=LINES,
        )
        violations = list(result.violations)
        good = result.good
        total = result.total
        estimated = result.estimated

        if len(line_spans(text)) == LINES:
            found, matched, checks, _estimated = scheme_violations(
                text, pack, SCHEME, allow_identical=False
            )
            keys = rhyme_keys(text, pack)
            found, exempted = _exempt_refrain_identicals(found, keys)
            violations += found
            good += matched + exempted
            total += checks

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "checks": float(total),
                "estimated_words": float(estimated),
            },
        )
