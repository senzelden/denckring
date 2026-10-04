"""Slenderizing — the source with every instance of one letter deleted."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import (
    ApplyParams,
    ConstructiveProcedure,
    DiacriticParams,
    SourceParams,
    plain,
)
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Produced, Report
from denckring.core.registry import register
from denckring.core.source_compare import aligned_report
from denckring.core.text import fold_letter, letter_spans, single_letter


class SlenderizingParams(SourceParams, DiacriticParams):
    deleted: str = Field(
        description="The letter removed from the source.", json_schema_extra=param("task", "letter")
    )

    @field_validator("deleted")
    @classmethod
    def _single_letter(cls, value: str) -> str:
        if len(value) != 1 or not value.isalpha():
            raise ValueError("deleted must be a single alphabetic character")
        return value.lower()


class SlenderizingApplyParams(SlenderizingParams, ApplyParams):
    pass


@register
class Slenderizing(ConstructiveProcedure[SlenderizingParams, SlenderizingApplyParams]):
    """Strike out one letter throughout and let the rest close up."""

    id = "slenderizing"
    rules = ("extra_letters", "missing_letter", "wrong_letter")

    @classmethod
    def params_model(cls) -> type[SlenderizingParams]:
        return SlenderizingParams

    def _check(self, text: str, pack: LanguagePack, params: SlenderizingParams) -> Report:
        fold = params.fold_diacritics
        deleted = single_letter(
            params.deleted, pack, fold=fold, procedure_id=self.id, field="deleted"
        )
        expected = [ch for _, ch in letter_spans(params.source, pack, fold=fold) if ch != deleted]
        spans = letter_spans(text, pack, fold=fold)
        # Aligned (ADR 0056), so a dropped letter costs one unit, not every letter
        # after it. Letters compare as `letter_spans` folds them and no further:
        # with `fold_diacritics` off, case is the writer's to keep. A letter
        # missing at the end is placed at the text's end, where it would go: every
        # violation here has a place, and an offset-less one left a caller nothing
        # to point at but the rule name.
        result = aligned_report(
            expected,
            spans,
            key=lambda letter: letter,
            substituted="wrong_letter",
            inserted="extra_letters",
            deleted="missing_letter",
            joiner="",
            end=len(text),
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"expected": float(len(expected)), "actual": float(len(spans))},
        )

    @classmethod
    def apply_params_model(cls) -> type[SlenderizingApplyParams]:
        return SlenderizingApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: SlenderizingApplyParams) -> Produced:
        """Strike the letter out of `text` and let the rest close up.

        Folds `deleted` the way `_check` folds it, and decides per source
        character by looking at *every* letter that character folds to — which
        it must, because `_check` works on the flattened letter stream and
        drops only the letters that match:

        - none of them is `deleted`: keep the source character untouched, so
          case and the ligature itself survive;
        - all of them are: drop it, which is what takes `ß` out with `s`;
        - some but not all: emit the survivors, folded, because there is no
          single character left that spells them.

        Dropping the whole character whenever *any* of its letters matched was
        the earlier rule. It agrees with `_check` only for a uniform fold, and
        `œ` is not uniform: `apply("Le cœur et la sœur", lang="fr",
        deleted="e")` gave `L cur t la sur`, whose own check scored 0.167 —
        the same broken thesis as the `ß` case one language over (ADR 0035,
        D6).

        No seed: there is exactly one slenderizing of a text for a given letter,
        which is why this generator takes no choices at all.
        """
        fold = params.fold_diacritics
        deleted = single_letter(
            params.deleted, pack, fold=fold, procedure_id=self.id, field="deleted"
        )
        out: list[str] = []
        for ch in text:
            if not ch.isalpha():
                out.append(ch)
                continue
            letters = fold_letter(ch, pack, fold=fold)
            if deleted not in letters:
                out.append(ch)
            else:
                out.append("".join(letter for letter in letters if letter != deleted))
        return plain(["".join(out)])
