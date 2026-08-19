"""Tmesis — a word split in two, with other material wedged between the halves.

*abso-bloody-lutely* is the textbook case: the halves ("abso", "lutely") rejoin
into a real word once the inserted material ("bloody") is removed, and it is that
rejoining — a lexicon membership test — that makes the row checkable at all. Task 1
corrected the catalogue row's `requires` to `[tokens, lexicon.words]` for exactly
this reason: nothing here needs `phonemes`, only `pack.is_word`.

A hyphenated run of `pack.word_re` tokens is the unit this scans, found with a
regex built from the pack's own token pattern rather than `word_spans`, which
would hand back "abso", "bloody" and "lutely" as three separate words and throw
away which ones flank the insertion.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

#: Two halves plus at least one inserted piece.
MIN_PARTS = 3


def _compound_spans(text: str, pack: LanguagePack) -> list[tuple[int, str]]:
    """Every hyphen-joined run of two or more tokens, as `(offset, text)`."""
    pattern = re.compile(rf"{pack.word_re.pattern}(?:-{pack.word_re.pattern})+")
    return [(m.start(), m.group()) for m in pattern.finditer(text)]


class TmesisParams(BaseModel):
    minimum: int = Field(
        default=1, ge=1, description="How many valid word-splits the text must carry."
    )


@register
class Tmesis(BaseProcedure[TmesisParams]):
    """A hyphenated compound must split into two halves that rejoin as a word."""

    id = "tmesis"

    @classmethod
    def params_model(cls) -> type[TmesisParams]:
        return TmesisParams

    def _check(self, text: str, pack: LanguagePack, params: TmesisParams) -> Report:
        compounds = _compound_spans(text, pack)
        violations: list[Violation] = []
        good = 0
        total = 0
        for offset, compound in compounds:
            total += 1
            parts = compound.split("-")
            if len(parts) < MIN_PARTS:
                violations.append(
                    Violation(
                        rule="no_material_inserted",
                        offset=offset,
                        found=compound,
                        expected="two halves with material inserted between them",
                    )
                )
                continue
            rejoined = (parts[0] + parts[-1]).casefold()
            if pack.is_word(rejoined):
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="halves_do_not_rejoin",
                        offset=offset,
                        found=rejoined,
                        expected="a word the lexicon knows",
                    )
                )
        # `total` only counts compounds actually present, so a text with none of
        # them at all would otherwise score a vacuous 1.0 — the same trap
        # `_report`'s docstring warns a procedure like this one must not fall
        # into. Bumping both `total` and `good`'s shortfall against `minimum`
        # closes it: an empty text, or one with fewer valid splits than
        # required, always scores below 1.0 and always carries the violation
        # that explains why.
        missing = max(params.minimum - good, 0)
        if missing:
            total += missing
            violations.append(
                Violation(
                    rule="too_few_splits",
                    offset=None,
                    found=f"{good} valid split(s)",
                    expected=f"at least {params.minimum}",
                )
            )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"compounds": float(len(compounds)), "valid_splits": float(good)},
        )
