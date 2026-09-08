"""Spenserian stanza — ABABBCBCC, eight pentameters and a closing alexandrine.

The last line is the form. A ninth pentameter is the error this checks for, so the
metre is per-line and `stanza_violations` does the scanning rather than `form_report`,
whose single `metre=` string cannot say "all but the last".
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, MetreParams, RhymeParams
from denckring.core.prosody import repeat_to, scheme_violations, stanza_violations, with_feminine
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register

SCHEME = "ABABBCBCC"
PENTAMETER = repeat_to("01", 5)
ALEXANDRINE = repeat_to("01", 6)


def patterns(feminine_ending: bool) -> list[list[str]]:
    """The readings acceptable for each of the nine lines.

    `stanza_violations` already takes a set per line, which is what makes the
    ninth line's alexandrine expressible at all; a feminine ending widens each
    of those sets rather than adding machinery (ADR 0040 D1).
    """
    return [with_feminine(PENTAMETER, feminine_ending)] * 8 + [
        with_feminine(ALEXANDRINE, feminine_ending)
    ]


class SpenserianStanzaParams(RhymeParams, MetreParams):
    pass


@register
class SpenserianStanza(BaseProcedure[SpenserianStanzaParams]):
    """Nine lines, the ninth one foot longer than the rest."""

    id = "spenserian_stanza"

    @classmethod
    def params_model(cls) -> type[SpenserianStanzaParams]:
        return SpenserianStanzaParams

    def _check(self, text: str, pack: LanguagePack, params: SpenserianStanzaParams) -> Report:
        metre = stanza_violations(text, pack, patterns(params.feminine_ending))
        # `stanza_violations` and `scheme_violations` each short-circuit on a
        # wrong line count, independently, so running both on a text of the wrong
        # length reported the same fault twice — one text, one length, two
        # identical violations. The metre scan's verdict is the one kept, matching
        # `form_report`, which returns after its own line-count check rather than
        # running the scheme as well.
        if any(violation.rule == "wrong_line_count" for violation in metre.violations):
            return self._report(
                good=metre.good,
                total=metre.total,
                violations=metre.violations,
                metrics={"checks": float(metre.total), "estimated_words": 0.0},
                evidence=list(metre.evidence),
            )
        found, matched, checks, _estimated, rhymes = scheme_violations(
            text, pack, SCHEME, allow_identical=False
        )
        return self._report(
            good=metre.good + matched,
            total=metre.total + checks,
            violations=metre.violations + found,
            metrics={
                "checks": float(metre.total + checks),
                "estimated_words": float(metre.estimated),
            },
            evidence=list(metre.evidence) + list(rhymes),
        )
