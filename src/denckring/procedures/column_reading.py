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

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import selection_report
from denckring.core.text import line_spans, word_spans


class ColumnReadingParams(SourceParams):
    # Defaulted to 1 rather than to some more "interesting" column: every
    # non-blank line, however short, has a first word, so `apply()` with no
    # extra keyword always has something to read — a higher default would
    # raise `NoCandidateWord` on any source whose shortest line falls under
    # it. Never named `seed` or `lang`: those collide with `apply`'s reserved
    # keyword arguments (see `diastic.DiasticParams.seed_phrase`'s comment for
    # the mechanism).
    column: int = Field(
        default=1, ge=1, description="Which word position to read down each line (1-based)."
    )


@register
class ColumnReading(BaseProcedure[ColumnReadingParams]):
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
        result = selection_report(chosen, params.source, pack)
        violations = list(result.violations)
        good = result.good
        total = result.total
        expected = self._column(params.source, pack, params.column)
        for index, word in enumerate(expected):
            total += 1
            if index < len(chosen) and chosen[index].casefold() == word.casefold():
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_column_word",
                        offset=chosen_spans[index][0] if index < len(chosen) else None,
                        found=chosen[index] if index < len(chosen) else "",
                        expected=word,
                        note=f"line {index + 1}'s word {params.column} should be {word!r}",
                    )
                )
        if len(chosen) > len(expected):
            violations.append(
                Violation(
                    rule="extra_words",
                    offset=chosen_spans[len(expected)][0],
                    found=" ".join(chosen[len(expected) :]),
                    expected="",
                )
            )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"selected": float(len(chosen))},
        )

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Read down `text`'s `column`th words, `text` serving as the source.

        Raises `NoCandidateWord` rather than returning an empty string when no
        line has a `column`th word: `_check` floors its denominator at 1, so an
        empty selection scores 0 rather than vacuously 1 — silently returning ""
        would hand back text its own checker rejects.
        """
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        pack = get_pack(lang)
        chosen = self._column(text, pack, parsed.column)
        if not chosen:
            raise NoCandidateWord(
                self.id,
                f"no line in the source has a word at column {parsed.column} — try a "
                "smaller column or a source with longer lines",
            )
        return " ".join(chosen)
