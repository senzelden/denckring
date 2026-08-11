"""Sator square — a grid reading identically in four directions."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans


class SatorSquareParams(DiacriticParams):
    pass


@register
class SatorSquare(BaseProcedure[SatorSquareParams]):
    """Checks the four-way symmetry only.

    Whether the rows are words is a lexical question this procedure does not
    ask — `word_square` declares `lexicon.nouns` for that and waits for it.
    An empty grid is unsatisfied: a square with no rows is not a square.
    """

    id = "sator_square"

    @classmethod
    def params_model(cls) -> type[SatorSquareParams]:
        return SatorSquareParams

    def _check(self, text: str, pack: LanguagePack, params: SatorSquareParams) -> Report:
        fold = params.fold_diacritics
        rows = [
            "".join(ch for _, ch in letter_spans(line, pack, fold=fold))
            for _, line in line_spans(text)
        ]
        violations: list[Violation] = []
        if not rows:
            violations.append(
                Violation(rule="empty_grid", offset=None, found="", expected="a square of letters")
            )
            return Report(
                procedure=self.id, satisfied=False, score=0.0, violations=violations, metrics={}
            )

        size = len(rows)
        checks = 0
        good = 0
        for row in rows:
            checks += 1
            if len(row) != size:
                violations.append(
                    Violation(
                        rule="wrong_row_length",
                        offset=None,
                        found=row,
                        expected=f"{size} letters",
                    )
                )
                continue
            good += 1
        if good < checks:
            return self._report(
                good=good, total=checks, violations=violations, metrics={"size": float(size)}
            )

        columns = ["".join(rows[r][c] for r in range(size)) for c in range(size)]
        comparisons = 0
        matches = 0
        for index in range(size):
            comparisons += 3
            if rows[index] == columns[index]:
                matches += 1
            else:
                violations.append(
                    Violation(
                        rule="row_column_mismatch",
                        offset=None,
                        found=rows[index],
                        expected=columns[index],
                    )
                )
            if rows[index] == rows[size - 1 - index][::-1]:
                matches += 1
            else:
                violations.append(
                    Violation(
                        rule="not_horizontally_palindromic",
                        offset=None,
                        found=rows[index],
                        expected=rows[size - 1 - index][::-1],
                    )
                )
            if columns[index] == columns[size - 1 - index][::-1]:
                matches += 1
            else:
                violations.append(
                    Violation(
                        rule="not_vertically_palindromic",
                        offset=None,
                        found=columns[index],
                        expected=columns[size - 1 - index][::-1],
                    )
                )
        return self._report(
            good=matches,
            total=comparisons,
            violations=violations,
            metrics={"size": float(size), "matches": float(matches)},
        )
