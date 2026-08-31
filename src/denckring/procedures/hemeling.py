"""Hemeling — an anagram of a name, explicated beneath it in rhymed verse.

Two constraints on one text, and the reason this row is worth having is that both
of them are checkable. Most of the combinatorial material in this catalogue has
one half a machine can judge and one half it cannot; Hemeling's title states the
compound rule outright — anagrams are to be made *und durch Reime zu erklähren* —
so the explication is not a gloss on the procedure but part of it.

Nothing here is new machinery. The first line is judged by `anagram`'s multiset
comparison and the rest by `rhyme_scheme`'s scheme walk, both imported rather than
reimplemented, so a text this row accepts is one those two rows accept.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams, RhymeParams, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.anagram import letter_counts, multiset_violations
from denckring.procedures.rhyme_scheme import form_report


class HemelingParams(SourceParams, DiacriticParams, RhymeParams):
    scheme: str = Field(
        default="AA",
        description="Rhyme pattern the explication must hold, one letter per line.",
    )
    allow_identical: bool = Field(
        default=False,
        description="Permit a word to rhyme with itself, as French rime riche does.",
    )

    @field_validator("scheme")
    @classmethod
    def _has_letters(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("scheme must contain at least one letter")
        return value


@register
class Hemeling(BaseProcedure[HemelingParams]):
    """The anagram on the first line, the rhymed explication under it.

    The two halves are scored together and reported separately, because they fail
    for unrelated reasons and a writer fixes them by different means: a letter
    surplus is arithmetic, a broken rhyme is not.

    `scheme` defaults to `AA` — a couplet, the shortest explication that can be
    said to rhyme at all. Hemeling prescribes no fixed length, so a default longer
    than the minimum would be this package inventing one.
    """

    id = "hemeling"

    @classmethod
    def params_model(cls) -> type[HemelingParams]:
        return HemelingParams

    def _check(self, text: str, pack: LanguagePack, params: HemelingParams) -> Report:
        lines = line_spans(text)
        wanted = 1 + len(params.scheme)
        if len(lines) != wanted:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count",
                        offset=None,
                        found=f"{len(lines)} lines",
                        expected=f"{wanted} lines: the anagram, then {len(params.scheme)}",
                    )
                ],
                metrics={"lines": float(len(lines)), "estimated_words": 0.0},
            )

        offset, anagram = lines[0]
        counted = letter_counts(anagram, pack, fold=params.fold_diacritics)
        letters, _, _ = multiset_violations(
            counted, letter_counts(params.source, pack, fold=params.fold_diacritics)
        )
        # `multiset_violations` reports letter by letter and carries no offset,
        # because `anagram` compares two whole texts. Here the anagram is one line
        # of several, so the line it is on is worth saying.
        found = [violation.model_copy(update={"offset": offset}) for violation in letters]
        # An anagram of nothing is not an anagram. `anagram._check` refuses the
        # empty candidate for the same reason: a text with no letters has nothing
        # surplus to report, so the multiset comparison alone cannot fail it.
        if not counted:
            found.append(
                Violation(
                    rule="empty_anagram",
                    offset=offset,
                    found="no letters",
                    expected=f"the letters of {params.source!r}",
                )
            )
        anagram_holds = not found

        gloss = "\n".join(line for _, line in lines[1:])
        rhyme = form_report(
            gloss,
            pack,
            scheme=params.scheme,
            allow_identical=params.allow_identical,
            unknown_rhyme=params.unknown_rhyme,
        )
        # The gloss's own offsets are relative to the gloss, which starts one line
        # into the text. Shifting them is what lets a caller point at the line.
        shift = lines[1][0]
        found += [
            violation.model_copy(
                update={"offset": None if violation.offset is None else violation.offset + shift}
            )
            for violation in rhyme.violations
        ]

        # One point for the anagram, then the rhyme's own tally. Weighting the two
        # halves equally would let a long explication drown a wrong anagram, or a
        # short one make it decisive; this is the same arithmetic the fixed forms
        # already use when they add a scheme to a metre.
        return self._report(
            good=int(anagram_holds) + rhyme.good,
            total=1 + rhyme.total,
            violations=found,
            metrics={
                "lines": float(len(lines)),
                "gloss_lines": float(len(lines) - 1),
                "estimated_words": float(rhyme.estimated),
            },
        )
