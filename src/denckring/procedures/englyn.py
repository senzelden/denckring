"""Englyn — a Welsh quatrain of ten, six, seven and seven syllables.

Syllabic, not accentual. Welsh metre counts syllables and this checks what the form
counts, so it uses the same helper `haiku` does rather than the stress scanner.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import scheme_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import pattern_result

PATTERN = [10, 6, 7, 7]


SCHEME = "AAAA"


class EnglynParams(RhymeParams):
    pass


@register
class Englyn(BaseProcedure[EnglynParams]):
    """Syllable pattern and the single rhyme. The cynghanedd is not code's business.

    *Unodl* means one rhyme: all four lines share it. Checking syllables alone would
    under-specify the form and leave the row's declared `phonemes` unreached
    (controller ruling R4).
    """

    id = "englyn"

    @classmethod
    def params_model(cls) -> type[EnglynParams]:
        return EnglynParams

    def _check(self, text: str, pack: LanguagePack, params: EnglynParams) -> Report:
        syllabic = pattern_result(text, pack, PATTERN)
        found, matched, checks, _estimated = scheme_violations(
            text, pack, SCHEME, allow_identical=False
        )
        return self._report(
            good=syllabic.good + matched,
            total=syllabic.total + checks,
            violations=syllabic.violations + found,
            metrics=syllabic.metrics,
        )
