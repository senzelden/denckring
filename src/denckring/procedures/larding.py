"""Larding — a new sentence inserted between every pair of existing ones, repeatedly.

Only half of that is checkable. That a new sentence sits between each pair of the
source's original sentences is mechanical: split both texts into sentences, and
confirm the source's sentences all appear in the result, in the same order, at
alternating positions — index 0, 2, 4 … of the result, one slot apart for each lard.
Whether the intercalated sentence *connects* the two it sits between, in the way
Oulipo's `Atlas de littérature potentielle` describes, is not decidable by this or
any program: no checker can tell that an inserted sentence bridges its neighbours
rather than merely occupying the slot between them. That half is not attempted —
an intercalated slot counts as filled the moment any non-blank sentence occupies
it, whatever it says.

`apply` is deliberately not shipped (ADR 0002 makes it optional even though the
catalogue marks this row `kind: both`): writing the intercalated sentence is
invention, not a mechanical transformation, so there is nothing here for a
generator to do that would not just be composing prose. Reading
`describe_procedure("larding")` and concluding this row can produce a larded text
would be a mistake this docstring exists to head off — `describe_procedure` still
reports `kind: both` (the catalogue's own classification of the form), but a model
that calls `apply_procedure("larding", …)` on the strength of that alone will get
an `AttributeError`-shaped absence, not a text.

The checkable claim is deliberately the single-pass one: the source's sentences at
alternating positions, exactly one lard between each pair, none trailing past the
last source sentence. The word "repeatedly" in the historical definition — larding
larded again — describes how the form was practised, not a further mechanical
invariant; nothing about a *second* pass is decidable from the result alone,
since by then every sentence, lard or source, looks the same as any other.
"""

from __future__ import annotations

import re

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

#: Same convention as `recombination`, `snowball_sentence` and
#: `sentence_length_constraint` — there is no shared sentence splitter in
#: `denckring.core.text` (only `letter_spans`, `word_spans`, `line_spans` and
#: `paragraph_spans` live there), so this row follows the established local
#: pattern rather than inventing a fifth one.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class LardingParams(SourceParams):
    pass


def _sentence_spans(text: str) -> list[tuple[int, str]]:
    """Every sentence as `(offset, text)`, offsets found by scanning forward.

    `SENTENCE_SPLIT` only tells us where to cut; the separator it consumes can be
    one space, a newline, or several of either, so the offset of each piece is
    recovered by searching for it in the original text from the previous match's
    end, the same offset-preserving discipline `denckring.core.text` uses.
    """
    spans: list[tuple[int, str]] = []
    cursor = 0
    for piece in SENTENCE_SPLIT.split(text.strip()):
        sentence = piece.strip()
        if not sentence:
            continue
        found = text.find(sentence, cursor)
        if found == -1:  # pragma: no cover - defensive; strip/find cannot miss
            found = cursor
        spans.append((found, sentence))
        cursor = found + len(sentence)
    return spans


@register
class Larding(BaseProcedure[LardingParams]):
    """Only the alternation is checkable; what the lards say is not.

    Checks that `params.source`'s sentences all appear in the result, unaltered
    and in order, at every even index (0, 2, 4, …) — with exactly one sentence
    of any content between each pair, and nothing trailing past the last one.
    """

    id = "larding"

    @classmethod
    def params_model(cls) -> type[LardingParams]:
        return LardingParams

    def _check(self, text: str, pack: LanguagePack, params: LardingParams) -> Report:
        source_spans = _sentence_spans(params.source)
        result_spans = _sentence_spans(text)
        source_norm = [s.strip().casefold() for _, s in source_spans]
        result_norm = [s.strip().casefold() for _, s in result_spans]

        total_source = len(source_norm)
        if total_source == 0:
            return self._report(
                good=0,
                total=0,
                violations=[],
                metrics={"source_sentences": 0.0, "result_sentences": float(len(result_norm))},
            )

        expected_length = 2 * total_source - 1
        violations: list[Violation] = []
        good = 0
        for index in range(expected_length):
            if index % 2 == 0:
                source_index = index // 2
                expected_sentence = source_norm[source_index]
                if index < len(result_norm) and result_norm[index] == expected_sentence:
                    good += 1
                else:
                    found = result_spans[index][1] if index < len(result_spans) else "(missing)"
                    offset = result_spans[index][0] if index < len(result_spans) else None
                    violations.append(
                        Violation(
                            rule="source_sentence_out_of_place",
                            offset=offset,
                            found=found,
                            expected=source_spans[source_index][1],
                        )
                    )
            elif index < len(result_norm):
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="missing_intercalated_sentence",
                        offset=None,
                        found="(missing)",
                        expected="a new sentence between these two",
                    )
                )

        if len(result_norm) != expected_length:
            violations.append(
                Violation(
                    rule="wrong_sentence_count",
                    offset=None,
                    found=f"{len(result_norm)} sentences",
                    expected=f"{expected_length} sentences "
                    "(one new sentence between each pair, nothing trailing)",
                )
            )

        # A result longer than expected inflates `total` past `good`'s ceiling,
        # so trailing material the check cannot otherwise evaluate still costs
        # score rather than passing free — invented material must be penalised,
        # not merely flagged by `wrong_sentence_count` while the score stays 1.0.
        total = max(expected_length, len(result_norm))
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "source_sentences": float(total_source),
                "result_sentences": float(len(result_norm)),
                "expected_sentences": float(expected_length),
            },
        )
