"""Mathews's algorithm — several texts tabled, each row rotated, then read across.

Harry Mathews's device sets several texts side by side, one per row of a
table, and rotates each row by a different amount before the table is read.
This row commits to one convention for "a different amount": rows are
0-indexed, and row *i* rotates left by *i* positions, modulo the row's own
length — row 0 is untouched, row 1 loses its first element to its own end,
row 2 loses its first two, and so on. "Read across" is taken row by row,
left to right, in row order: the output is row 0's rotated words, then row
1's, then row 2's, with nothing in between to mark the seam — the table's
edges are the only structure that survives.

`source` holds the several texts as blank-line separated paragraphs, one per
row, each split into words the same way `every_nth_word` splits its source —
by `word_spans`, casefolded, since the rotation moves elements, not letters.
Rows are trimmed to the shortest row's length before rotating, so the table
is rectangular: an element beyond that width was never several texts' common
ground and is not part of what gets rotated or read. That rectangle's words,
not every word of every source paragraph, are what `rearrangement_report`
checks `text` against — the same reasoning `text_folding` gives for comparing
against its two flaps rather than the untouched remainder past `fold_at`.

Purely mechanical, and fully generative: given at least two rows with at
least one column between them, `apply` has no choice to make and nothing to
search for, unlike the selection-based rows that can run out of candidates.
"""

from __future__ import annotations

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import rearrangement_report
from denckring.core.text import paragraph_spans, word_spans


class MathewsAlgorithmParams(SourceParams):
    """No fields beyond `source`: the table's rows live inside it (see the
    module docstring), and the rotation-by-row-index convention is fixed."""


class MathewsAlgorithmApplyParams(MathewsAlgorithmParams, ApplyParams):
    pass


@register
class MathewsAlgorithm(ConstructiveProcedure[MathewsAlgorithmParams, MathewsAlgorithmApplyParams]):
    """Constructive: `apply` performs the rotation that `check` verifies."""

    id = "mathews_algorithm"

    @classmethod
    def params_model(cls) -> type[MathewsAlgorithmParams]:
        return MathewsAlgorithmParams

    @staticmethod
    def _table(source: str, pack: LanguagePack) -> list[list[str]]:
        """`source`'s paragraphs as a rectangular table of casefolded words,
        each row trimmed to the shortest row's length."""
        rows = [
            [word.casefold() for _, word in word_spans(block, pack)]
            for _, block in paragraph_spans(source)
        ]
        width = min((len(row) for row in rows), default=0)
        return [row[:width] for row in rows]

    @staticmethod
    def _rotate(row: list[str], amount: int) -> list[str]:
        """`row` shifted left by `amount`, modulo its own length."""
        if not row:
            return row
        shift = amount % len(row)
        return row[shift:] + row[:shift]

    def _rotated(self, table: list[list[str]]) -> list[str]:
        """The table read across: row *i* rotated by *i*, rows concatenated in order."""
        return [word for index, row in enumerate(table) for word in self._rotate(row, index)]

    def _check(self, text: str, pack: LanguagePack, params: MathewsAlgorithmParams) -> Report:
        actual_spans = word_spans(text, pack)
        table = self._table(params.source, pack)
        table_words = [word for row in table for word in row]

        result = rearrangement_report([word.casefold() for _, word in actual_spans], table_words)
        violations = list(result.violations)
        good = result.good
        total = result.total

        expected = self._rotated(table)
        for index, (offset, word) in enumerate(actual_spans):
            total += 1
            folded = word.casefold()
            if index < len(expected) and folded == expected[index]:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="word_out_of_rotation",
                        offset=offset,
                        found=folded,
                        expected=expected[index] if index < len(expected) else "",
                        note=f"position {index + 1} after rotating each row by its index",
                    )
                )

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "rows": float(len(table)),
                "columns": float(len(table[0]) if table else 0),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[MathewsAlgorithmApplyParams]:
        return MathewsAlgorithmApplyParams

    def _produce(
        self, text: str, pack: LanguagePack, params: MathewsAlgorithmApplyParams
    ) -> Produced:
        """Table and rotate `text`'s rows, `text` serving as its own source.

        `text` must itself hold at least two blank-line separated paragraphs,
        sharing at least one column between them — see the module docstring.
        Raises `NoCandidateWord` rather than returning `text` unchanged when
        it does not: a table needs two rows to rotate against each other,
        and a column to read across.
        """
        table = self._table(text, pack)
        if len(table) < 2 or not table[0]:
            raise NoCandidateWord(
                self.id,
                "the source does not hold at least two blank-line separated "
                "texts sharing at least one word of common width — a table "
                "needs two rows and a column to rotate, so give a source "
                "with two or more such paragraphs, or check a text instead "
                "of generating one",
            )
        return plain(
            ["\n".join(" ".join(self._rotate(row, index)) for index, row in enumerate(table))]
        )
