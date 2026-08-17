"""Word square — a grid reading the same across as down, of real words."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans


class WordSquareParams(BaseModel):
    pass


@register
class WordSquare(BaseProcedure[WordSquareParams]):
    """`sator_square` checks the symmetry; this also asks whether the rows are words.

    An empty grid is unsatisfied: a square with no rows is not a square.
    """

    id = "word_square"

    @classmethod
    def params_model(cls) -> type[WordSquareParams]:
        return WordSquareParams

    def _check(self, text: str, pack: LanguagePack, params: WordSquareParams) -> Report:
        # fold=False: the lexicon stores each language's own diacritics
        # (German umlauts included), so folding before the query would
        # make every umlaut word unfindable and could assemble a false
        # positive from pieces not actually present in the text.
        rows = [
            "".join(ch for _, ch in letter_spans(line, pack, fold=False))
            for _, line in line_spans(text)
        ]
        if not rows:
            return Report(
                procedure=self.id,
                satisfied=False,
                score=0.0,
                violations=[
                    Violation(
                        rule="empty_grid", offset=None, found="", expected="a square of words"
                    )
                ],
                metrics={},
            )

        size = len(rows)
        violations: list[Violation] = []
        checks = 0
        good = 0
        for row in rows:
            checks += 1
            if len(row) != size:
                violations.append(
                    Violation(
                        rule="wrong_row_length", offset=None, found=row, expected=f"{size} letters"
                    )
                )
            else:
                good += 1
        if good < checks:
            return self._report(
                good=good, total=checks, violations=violations, metrics={"size": float(size)}
            )

        columns = ["".join(rows[r][c] for r in range(size)) for c in range(size)]
        for index in range(size):
            checks += 1
            if rows[index] == columns[index]:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="row_column_mismatch",
                        offset=None,
                        found=rows[index],
                        expected=columns[index],
                    )
                )
        for row in rows:
            checks += 1
            if pack.is_word(row):
                good += 1
            else:
                violations.append(
                    Violation(rule="not_a_word", offset=None, found=row, expected="a word")
                )
        return self._report(
            good=good, total=checks, violations=violations, metrics={"size": float(size)}
        )
