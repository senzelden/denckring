"""Clerihew — four lines rhyming AABB, the first naming a person.

**No metre check, deliberately.** The clerihew's metre is irregular by design; the
lopsidedness is the joke. A metre check here would reject every real clerihew,
including Bentley's own.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import scheme_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.text import line_spans

SCHEME = "AABB"
LINES = 4


class ClerihewParams(RhymeParams):
    pass


@register
class Clerihew(BaseProcedure[ClerihewParams]):
    """Rhyme and line count only."""

    id = "clerihew"

    @classmethod
    def params_model(cls) -> type[ClerihewParams]:
        return ClerihewParams

    def _check(self, text: str, pack: LanguagePack, params: ClerihewParams) -> Report:
        found, matched, checks, _estimated = scheme_violations(
            text, pack, SCHEME, allow_identical=False
        )
        return self._report(
            good=matched,
            total=checks,
            violations=found,
            metrics={"lines": float(len(line_spans(text)))},
        )
