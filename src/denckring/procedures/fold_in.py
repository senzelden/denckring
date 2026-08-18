"""Fold-in — one page folded lengthwise onto another and read across the join.

William S. Burroughs describes taking two separate pages and folding one onto
the other, so a single reading runs across the seam between them instead of
down either page alone. That is a physical operation on two sheets, not a
rule stated in code terms, and `check` takes one text plus a `source`, not
two — so this row commits to one reading of both halves of that gap.

The two pages are modelled as `source` itself: the first two blank-line
separated paragraphs of `source` are page one and page two (any further
paragraphs are ignored, the same tolerance `text_folding` shows a `fold_at`
past the source's own length). Reading "across the join" is taken literally,
line by line: the folded reading is page one's first line, then page two's
first line, then page one's second line, then page two's second line, and so
on, alternating for as long as both pages still have a line to offer. Once
one page runs out, the other page's remaining lines continue in their own
order — there is no line left on the far side of the fold to alternate
against. Every line of both pages appears exactly once; only their order is
new, which is what keeps this row on `rearrangement_report`, built for
exactly that shape, alongside `boustrophedon` and `text_folding`.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import rearrangement_report
from denckring.core.text import line_spans, paragraph_spans, word_spans


class FoldInParams(SourceParams):
    """No fields beyond `source`: the two pages live inside it (see the module
    docstring), and the alternation rule that folds them together is fixed,
    not a dial a caller turns."""


@register
class FoldIn(BaseProcedure[FoldInParams]):
    """Constructive: `apply` performs the fold-in that `check` verifies."""

    id = "fold_in"

    @classmethod
    def params_model(cls) -> type[FoldInParams]:
        return FoldInParams

    @staticmethod
    def _pages(source: str) -> tuple[list[str], list[str]]:
        """The first two paragraphs of `source`, each as its own list of lines."""
        blocks = paragraph_spans(source)
        page_one = [line for _, line in line_spans(blocks[0][1])] if len(blocks) > 0 else []
        page_two = [line for _, line in line_spans(blocks[1][1])] if len(blocks) > 1 else []
        return page_one, page_two

    @staticmethod
    def _fold_in(page_one: list[str], page_two: list[str]) -> list[str]:
        """Page one's line *i*, then page two's line *i*, for increasing *i*.

        Once the shorter page is exhausted, the longer page's remaining lines
        continue in order — there is nothing left on the other side of the
        fold to alternate with.
        """
        folded: list[str] = []
        for index in range(max(len(page_one), len(page_two))):
            if index < len(page_one):
                folded.append(page_one[index])
            if index < len(page_two):
                folded.append(page_two[index])
        return folded

    def _check(self, text: str, pack: LanguagePack, params: FoldInParams) -> Report:
        text_lines = line_spans(text)
        page_one, page_two = self._pages(params.source)
        result = rearrangement_report([line for _, line in text_lines], page_one + page_two)
        violations = list(result.violations)
        good = result.good
        total = result.total

        expected_order = self._fold_in(page_one, page_two)
        for index, (offset, line) in enumerate(text_lines):
            total += 1
            if index < len(expected_order) and line == expected_order[index]:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="line_out_of_join",
                        offset=offset,
                        found=line,
                        expected=expected_order[index] if index < len(expected_order) else "",
                        note=f"position {index + 1} after folding the two pages together",
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

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Fold `text`'s two pages together, `text` serving as its own source.

        `text` must itself hold two blank-line separated paragraphs — see the
        module docstring. Raises `NoCandidateWord` rather than returning
        `text` unchanged when it does not: a fold-in needs two pages to bring
        together, and one paragraph, or none, offers only a single flap.
        """
        self.parse_params({"source": text, **params})
        page_one, page_two = self._pages(text)
        if not page_one or not page_two:
            raise NoCandidateWord(
                self.id,
                "the source does not hold two blank-line separated pages, each "
                "with at least one line — a fold-in needs a page on each side "
                "of the join, so give a source with two such paragraphs, or "
                "check a text instead of generating one",
            )
        return "\n".join(self._fold_in(page_one, page_two))
