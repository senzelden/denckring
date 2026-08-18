"""Haikuization — keep only the rhyme-words or line ends, discard the rest.

The catalogue's own words: "a reduction that keeps only the rhyme-words or
line ends of an existing poem, leaving a shorter poem inside the longer one."
Task 1 corrected this row's `requires` to include `phonemes`, so the reading
implemented here has to genuinely reach a pronunciation, not just count
letters at a line's end — `denckring.core.prosody.rhyme_keys` is what does
that: for every line it returns the line's final word together with every
rhyme key that word's pronunciation can take. It always returns that final
word, whether or not the poem actually rhymes anything against it, which is
exactly why one function serves both halves of the catalogue's "or": the
"rhyme-word" reading and the "line end" reading are the same word here, and
`rhyme_keys` is where a genuine phonemic answer would show up if this row
ever needed to test rhyme rather than merely locate the candidate word — a
later, stricter row could ask whether two of those key sets intersect, as
`scheme_violations` does; this one does not, because "leaving a shorter poem
inside the longer one" only needs the words identified, not verified against
each other.

Built on `selection_report`, the same helper `diastic`, `mesostic` and
`column_reading` share: the words come from the source in order, and the
row-specific rule — here, each chosen word must be its line's ending — is
layered on top.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.prosody import rhyme_keys
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import selection_report
from denckring.core.text import word_spans


class HaikuizationParams(SourceParams):
    """No row-specific field: which word is kept is not a caller's choice —
    unlike `column_reading`'s `column`, it is always the line end. A named
    subclass of `SourceParams` still, rather than `SourceParams` itself, so
    every row's params type is its own and adding a field later costs
    nothing at the call sites.
    """


@register
class Haikuization(BaseProcedure[HaikuizationParams]):
    """Constructive: `apply` performs the reduction `check` verifies."""

    id = "haikuization"

    @classmethod
    def params_model(cls) -> type[HaikuizationParams]:
        return HaikuizationParams

    def _check(self, text: str, pack: LanguagePack, params: HaikuizationParams) -> Report:
        chosen_spans = word_spans(text, pack)
        chosen = [word for _, word in chosen_spans]
        result = selection_report(chosen, params.source, pack)
        violations = list(result.violations)
        good = result.good
        total = result.total
        expected = [word for _, word, _ in rhyme_keys(params.source, pack)]
        for index, word in enumerate(expected):
            total += 1
            if index < len(chosen) and chosen[index].casefold() == word.casefold():
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="not_a_line_end",
                        offset=chosen_spans[index][0] if index < len(chosen) else None,
                        found=chosen[index] if index < len(chosen) else "",
                        expected=word,
                        note=f"line {index + 1} ends in {word!r}",
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
        """Keep only the last word of every line of `text`, which serves as the source.

        Calls `rhyme_keys` rather than reading `line_spans` and tokenizing by
        hand, so this generator exercises the same phonemic lookup its own
        `_check` does — a generator that took the cheaper, letters-only route
        would produce text its declared `phonemes` requirement was never
        needed to accept. Raises `NoCandidateWord` rather than returning an
        empty string when the source has no non-blank line to read from:
        `_check` floors its denominator at 1, so an empty selection scores 0
        rather than vacuously 1 — silently returning "" would hand back text
        its own checker rejects.
        """
        from denckring.lang import get_pack

        self.parse_params({"source": text, **params})
        pack = get_pack(lang)
        chosen = [word for _, word, _ in rhyme_keys(text, pack)]
        if not chosen:
            raise NoCandidateWord(
                self.id,
                "the source has no non-blank line to read a rhyme-word or line end "
                "from — try a source with at least one line of text",
            )
        return " ".join(chosen)
