"""Eodermdrome — the letters trace a closed walk using each edge once."""

from __future__ import annotations

from itertools import pairwise

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans

MIN_LETTERS = 2

#: How the default minimum has always read in a `too_short` violation, kept so a
#: 0.3.2 report at the default is byte for byte a 0.3.1 one.
_SPELLED = {MIN_LETTERS: "two"}


class EodermdromeParams(DiacriticParams):
    # A9: `dead` passes, a closed walk over three letters. Opt-in, so the
    # default keeps the two letters a walk needs to have an edge at all.
    min_letters: int = Field(
        default=MIN_LETTERS,
        ge=MIN_LETTERS,
        description="Fewest letters the text must have. The default, 2, accepts `dead`.",
    )


@register
class Eodermdrome(BaseProcedure[EodermdromeParams]):
    """Borgmann's graph-theoretic word form.

    Read the letters as a walk over a graph whose vertices are the distinct
    letters and whose edges are consecutive pairs. The word qualifies when the
    walk uses no edge twice and returns to the letter it started from. Whether
    the resulting graph is non-planar — Borgmann's stricter reading — is not
    checked here, and the catalogue definition says so.
    """

    id = "eodermdrome"
    rules = ("not_closed", "repeated_edge", "too_short")

    @classmethod
    def params_model(cls) -> type[EodermdromeParams]:
        return EodermdromeParams

    def _check(self, text: str, pack: LanguagePack, params: EodermdromeParams) -> Report:
        letters = [ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics)]
        violations: list[Violation] = []
        if len(letters) < params.min_letters:
            least = _SPELLED.get(params.min_letters, str(params.min_letters))
            return Report(
                procedure=self.id,
                satisfied=False,
                score=0.0,
                violations=[
                    Violation(
                        rule="too_short",
                        offset=None,
                        found=text,
                        expected=f"at least {least} letters",
                    )
                ],
                metrics={"letters": float(len(letters))},
            )

        edges = [frozenset((a, b)) for a, b in pairwise(letters) if a != b]
        seen: set[frozenset[str]] = set()
        repeats = 0
        for edge in edges:
            if edge in seen:
                repeats += 1
                violations.append(
                    Violation(
                        rule="repeated_edge",
                        offset=None,
                        found="".join(sorted(edge)),
                        expected="an unused letter pair",
                    )
                )
            seen.add(edge)
        closed = letters[0] == letters[-1]
        if not closed:
            violations.append(
                Violation(rule="not_closed", offset=None, found=letters[-1], expected=letters[0])
            )
        total = len(edges) + 1
        return self._report(
            good=total - repeats - (0 if closed else 1),
            total=total,
            violations=violations,
            metrics={"edges": float(len(edges)), "repeated": float(repeats)},
        )
