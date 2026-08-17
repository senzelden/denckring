"""Pangrammatic window — every letter, inside a stated span."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class PangrammaticWindowParams(DiacriticParams):
    #: Required rather than defaulted. "As short as possible" is not decidable
    #: from one text, and without a bar this procedure is `pangram` under a
    #: second name — so the caller states the bar, as ADR 0009 makes editorial
    #: choices parameters rather than hidden constants.
    max_length: int = Field(ge=26, description="The longest window that still counts.")


@register
class PangrammaticWindow(BaseProcedure[PangrammaticWindowParams]):
    """Word Ways' hunt: a naturally occurring run holding the whole alphabet.

    Like `pangram`, an empty text is unsatisfied rather than vacuous — it
    requires something instead of forbidding something, so an empty text
    supplies none of it. That is why this builds its Report directly.
    """

    id = "pangrammatic_window"

    @classmethod
    def params_model(cls) -> type[PangrammaticWindowParams]:
        return PangrammaticWindowParams

    def _check(self, text: str, pack: LanguagePack, params: PangrammaticWindowParams) -> Report:
        alphabet = pack.alphabet()
        letters = [
            ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics) if ch in alphabet
        ]
        present = set(letters)
        missing = [ch for ch in alphabet if ch not in present]

        violations = [
            Violation(
                rule="missing_letter",
                offset=None,
                found="",
                expected=f"{ch!r} somewhere in the window",
            )
            for ch in missing
        ]
        if len(letters) > params.max_length:
            violations.append(
                Violation(
                    rule="window_too_long",
                    offset=None,
                    found=f"{len(letters)} letters",
                    expected=f"at most {params.max_length}",
                )
            )
        satisfied = not violations
        coverage = (len(alphabet) - len(missing)) / len(alphabet)
        excess = max(0, len(letters) - params.max_length)
        # Both rules feed one score, so that a text passing one but not the
        # other still ends up with score < 1.0 — `satisfied` must always agree
        # with `score == 1.0`, and this is the one procedure that cannot lean
        # on `_report` to enforce that for it. A text at coverage 1.0 but over
        # the bar would otherwise score a perfect 1.0 while `satisfied` says
        # no — a contradiction, not just an edge case.
        score = coverage * len(alphabet) / (len(alphabet) + excess)
        return Report(
            procedure=self.id,
            satisfied=satisfied,
            score=score,
            violations=violations,
            metrics={"letters": float(len(letters)), "missing": float(len(missing))},
        )
