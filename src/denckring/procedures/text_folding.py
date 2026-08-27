"""Text folding — a page folded so non-adjacent passages meet and are read as
continuous.

William S. Burroughs describes folding a page and reading down across the
seam, so that passages once far apart on the sheet become continuous. That is
a physical operation, not a rule stated in code terms, so this row commits to
one reading of it: the source's lines are split into two flaps at `fold_at` (a
1-based line count) — the *near* flap holds the first `fold_at` lines, the
*far* flap holds the rest. The fold brings the far flap to rest against the
near flap, so the folded reading is the far flap's lines, in their original
order, followed by the near flap's lines, in their original order. Each
flap's internal order survives untouched; only the seam is new — the far
flap's last line, once the end of the source, now sits beside the near
flap's first line, once its beginning. That is what a single physical fold
does: one new junction, not a shuffle of every line on the page.

Built on `rearrangement_report`, the same helper `boustrophedon` was
hand-written against first: the lines come from the source, and the fold
rule — the one thing that varies row to row — is layered on top, exactly as
`boustrophedon`'s turning rule is.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import rearrangement_report
from denckring.core.text import line_spans, word_spans


class TextFoldingParams(SourceParams):
    # Defaulted to 1, like `column_reading.column`, so `apply()` with no extra
    # keyword always has two flaps to fold as long as the source has at least
    # two lines.
    fold_at: int = Field(
        default=1,
        ge=1,
        description="How many lines make up the near flap; the far flap folds onto it.",
    )


class TextFoldingApplyParams(TextFoldingParams, ApplyParams):
    pass


@register
class TextFolding(ConstructiveProcedure[TextFoldingParams, TextFoldingApplyParams]):
    """Constructive: `apply` performs the fold that `check` verifies."""

    id = "text_folding"

    @classmethod
    def params_model(cls) -> type[TextFoldingParams]:
        return TextFoldingParams

    @staticmethod
    def _fold(lines: list[str], fold_at: int) -> list[str]:
        """`lines` after folding: the far flap first, then the near flap.

        Clamped to `[0, len(lines)]` rather than raising on an out-of-range
        `fold_at`: a fold past the source's own length degrades to the far
        flap being empty — the source in its original order — rather than an
        error, the same tolerance `column_reading` shows a `column` beyond
        any line's length.
        """
        cut = min(max(fold_at, 0), len(lines))
        return lines[cut:] + lines[:cut]

    def _check(self, text: str, pack: LanguagePack, params: TextFoldingParams) -> Report:
        text_lines = line_spans(text)
        source_lines = [line for _, line in line_spans(params.source)]
        result = rearrangement_report([line for _, line in text_lines], source_lines)
        violations = list(result.violations)
        good = result.good
        total = result.total

        expected_order = self._fold(source_lines, params.fold_at)
        for index, (offset, line) in enumerate(text_lines):
            total += 1
            if index < len(expected_order) and line == expected_order[index]:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="line_out_of_fold",
                        offset=offset,
                        found=line,
                        expected=expected_order[index] if index < len(expected_order) else "",
                        note=f"position {index + 1} after folding at line {params.fold_at}",
                    )
                )

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "lines": float(len(text_lines)),
                "words": float(len(word_spans(text, pack))),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[TextFoldingApplyParams]:
        return TextFoldingApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: TextFoldingApplyParams) -> list[str]:
        """Fold `text` at `fold_at`, `text` serving as its own source.

        Raises `NoCandidateWord` rather than returning `text` unchanged when
        it has fewer than two lines: a fold needs two flaps to bring
        together, and a single line offers only one.
        """
        lines = [line for _, line in line_spans(text)]
        if len(lines) < 2:
            raise NoCandidateWord(
                self.id,
                "the source has fewer than two lines — a fold needs a near flap "
                "and a far flap to bring together, so give a source with at "
                "least two lines, or check a text instead of generating one",
            )
        return ["\n".join(self._fold(lines, params.fold_at))]
