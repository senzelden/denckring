"""Column reading — the nth word of every line, read down.

The catalogue describes this as taking "a printed page vertically rather than
horizontally, so the column rather than the line becomes the unit." That is a
physical operation on a printed page, not a rule stated in code terms — the
row commits to one reading of it: the source is split into lines, and the
`column`th word (1-based) of each line, read down in line order, is the
column. A line with fewer than `column` words has no word to contribute at
that column and is skipped rather than padded — the alternative, treating a
short line's missing word as a blank to preserve alignment, has no textual
representation `selection_report` could compare against a real word, so it
would have to be invented rather than read.

Built on `selection_report`, the same helper `diastic` and `mesostic` share:
the words come from the source in order, and the column rule — the one thing
that varies row to row — is layered on top, exactly as `diastic`'s positional
letter rule and `mesostic`'s spine-in-line rule are.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.source_compare import positional_report, selection_report
from denckring.core.text import line_spans, word_spans


class ColumnReadingParams(SourceParams):
    # Defaulted to 1 rather than to some more "interesting" column: every
    # non-blank line, however short, has a first word, so `apply()` with no
    # extra keyword always has something to read — a higher default would
    # raise `NoCandidateWord` on any source whose shortest line falls under it.
    column: int = Field(
        default=1, ge=1, description="Which word position to read down each line (1-based)."
    )


class ColumnReadingApplyParams(ColumnReadingParams, ApplyParams):
    pass


@register
class ColumnReading(ConstructiveProcedure[ColumnReadingParams, ColumnReadingApplyParams]):
    """Constructive: `apply` performs the vertical reading `check` verifies."""

    id = "column_reading"

    @classmethod
    def params_model(cls) -> type[ColumnReadingParams]:
        return ColumnReadingParams

    @staticmethod
    def _column(source: str, pack: LanguagePack, column: int) -> list[str]:
        """The `column`th word of every line of `source` that has one, in line order."""
        chosen: list[str] = []
        for _, line in line_spans(source):
            words = [word for _, word in word_spans(line, pack)]
            if len(words) >= column:
                chosen.append(words[column - 1])
        return chosen

    def _check(self, text: str, pack: LanguagePack, params: ColumnReadingParams) -> Report:
        chosen_spans = word_spans(text, pack)
        chosen = [word for _, word in chosen_spans]
        drawn = selection_report(chosen_spans, params.source, pack)
        column = params.column
        placed = positional_report(
            chosen_spans,
            self._column(params.source, pack, column),
            rule="wrong_column_word",
            note=lambda index, word: f"line {index + 1}'s word {column} should be {word!r}",
        )
        return self._report(
            good=drawn.good + placed.good,
            total=max(drawn.total + placed.total, 1),
            violations=drawn.violations + placed.violations,
            metrics={"selected": float(len(chosen))},
        )

    @classmethod
    def apply_params_model(cls) -> type[ColumnReadingApplyParams]:
        return ColumnReadingApplyParams

    def _produce(
        self, text: str, pack: LanguagePack, params: ColumnReadingApplyParams
    ) -> list[str]:
        """Read down `text`'s `column`th words, `text` serving as the source.

        Raises `NoCandidateWord` rather than returning an empty string when no
        line has a `column`th word: `_check` floors its denominator at 1, so an
        empty selection scores 0 rather than vacuously 1 — silently returning ""
        would hand back text its own checker rejects.
        """
        chosen = self._column(text, pack, params.column)
        if not chosen:
            raise NoCandidateWord(
                self.id,
                f"no line in the source has a word at column {params.column} — try a "
                "smaller column or a source with longer lines",
            )
        return [" ".join(chosen)]
