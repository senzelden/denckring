"""Fold-in — one page folded lengthwise onto another and read across the join.

William S. Burroughs and Brion Gysin describe a *lengthwise* fold: the crease
runs down the page, not across it, so what meets at the join is the left half
of one sheet against the right half of another, line by line. Reading down
the folded pair, each line is only ever half of what either source line said
— the other half is folded under and gone. That loss is not a defect this
row needs to paper over; it is the form. (An earlier draft of this row put
the fold on `rearrangement_report` and read it as a full-line alternation
that kept every word of both pages — that reading was ruled out: it matches
neither Burroughs's own description nor the catalogue's `prompt_hints`, and
it is not, in fact, a rearrangement at all, but a selection-and-merge that
happened to fit the helper's shape. This row does not use
`rearrangement_report`.)

The two pages are modelled as `source`, exactly as before: the first two
blank-line separated paragraphs of `source` are page one and page two (any
further paragraphs are ignored, the same tolerance `text_folding` shows a
`fold_at` past the source's own length).

For each line index shared by both pages — up to whichever page has fewer
lines; a page's lines past the other page's end have nothing to fold against
and are simply never read — the folded line is page one's line's **left
half**, word for word, joined to page two's line's **right half**. A line's
own word count decides its own split point, independent of the other page's
line: split = `ceil(word_count / 2)`, so the left half of *that* line is its
first `split` words and the right half is its remaining, smaller-or-equal
half. The same rule, applied to each source line on its own terms, is what
both "left half of page one" and "right half of page two" mean here. Words
are plain whitespace-split tokens, not the language pack's tokenizer: a
physical fold divides a line of running text by eye, not by lemma.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, paragraph_spans, word_spans


class FoldInParams(SourceParams):
    """No fields beyond `source`: the two pages live inside it (see the module
    docstring), and the half-and-join rule that folds them together is
    fixed, not a dial a caller turns."""


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
    def _halves(line: str) -> tuple[list[str], list[str]]:
        """`line`'s words split at `ceil(word_count / 2)`: left half, right half."""
        words = line.split()
        split = (len(words) + 1) // 2
        return words[:split], words[split:]

    @classmethod
    def _fold_in(cls, page_one: list[str], page_two: list[str]) -> list[str]:
        """Page one's left half joined to page two's right half, line by line.

        Only as many lines as the shorter page offers: a line on the longer
        page past that point has no partner to fold against.
        """
        folded: list[str] = []
        for index in range(min(len(page_one), len(page_two))):
            left, _ = cls._halves(page_one[index])
            _, right = cls._halves(page_two[index])
            folded.append(" ".join(left + right))
        return folded

    def _check(self, text: str, pack: LanguagePack, params: FoldInParams) -> Report:
        text_lines = line_spans(text)
        page_one, page_two = self._pages(params.source)
        expected = self._fold_in(page_one, page_two)

        violations: list[Violation] = []
        matched = 0
        for index, (offset, line) in enumerate(text_lines):
            if index < len(expected) and line == expected[index]:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="not_the_fold",
                        offset=offset,
                        found=line,
                        expected=expected[index] if index < len(expected) else "",
                        note=(
                            f"line {index + 1} must join page one's left half "
                            "to page two's right half"
                        ),
                    )
                )
        for index in range(len(text_lines), len(expected)):
            violations.append(
                Violation(
                    rule="not_the_fold",
                    offset=None,
                    found="",
                    expected=expected[index],
                    note=f"line {index + 1} is missing",
                )
            )

        return self._report(
            good=matched,
            total=max(len(expected), len(text_lines)),
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
