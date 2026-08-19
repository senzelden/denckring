"""Haikuization — keep only the line ends of an existing poem, discard the rest.

The catalogue's own words: "a reduction that keeps only the rhyme-words or
line ends of an existing poem, leaving a shorter poem inside the longer one."
That reads as two distinct readings, but only one is checked here: the line
ends. `phonemes` was briefly required by an earlier correction on the
assumption a "rhyme-word" reading could be told apart from a "line end" one
— it cannot, in this codebase. `denckring.core.prosody.rhyme_keys` always
resolves each line to its final word regardless of whether that word
pronounces as a rhyme with anything else; it never tells two lines' words
apart by whether they actually rhyme, so calling it bought a phoneme lookup
that never affected any verdict, only fragility on a line-ending word outside
the pronouncing dictionary. This row now reads line ends directly — by
`line_spans` and `word_spans`, not `rhyme_keys` — and declares `tokens` only.
A future row that genuinely tests rhyme (two lines' keys intersecting, as
`scheme_violations` does) would be a different, stricter procedure than
"leaving a shorter poem inside the longer one" asks for.

Built on `selection_report`, the same helper `diastic`, `mesostic` and
`column_reading` share: the words come from the source in order, and the
row-specific rule — here, each chosen word must be its line's ending — is
layered on top.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report
from denckring.core.registry import register
from denckring.core.source_compare import positional_report, selection_report
from denckring.core.text import line_spans, word_spans


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

    @staticmethod
    def _line_ends(source: str, pack: LanguagePack) -> list[str]:
        """Every non-blank line's last word, in line order.

        No lexicon or phoneme lookup: an invented word such as "flurbish" is
        as good a line end as a dictionary one — this row only locates the
        word, it does not pronounce it.
        """
        ends: list[str] = []
        for _, line in line_spans(source):
            words = [word for _, word in word_spans(line, pack)]
            if words:
                ends.append(words[-1])
        return ends

    def _check(self, text: str, pack: LanguagePack, params: HaikuizationParams) -> Report:
        chosen_spans = word_spans(text, pack)
        chosen = [word for _, word in chosen_spans]
        drawn = selection_report(chosen_spans, params.source, pack)
        placed = positional_report(
            chosen_spans,
            self._line_ends(params.source, pack),
            rule="wrong_line_end",
            note=lambda index, word: f"line {index + 1} ends in {word!r}",
        )
        violations = drawn.violations + placed.violations
        good = drawn.good + placed.good
        total = drawn.total + placed.total
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

        Raises `NoCandidateWord` rather than returning an empty string when
        the source has no non-blank line to read from: `_check` floors its
        denominator at 1, so an empty selection scores 0 rather than
        vacuously 1 — silently returning "" would hand back text its own
        checker rejects.
        """
        from denckring.lang import get_pack

        self.parse_params({"source": text, **params})
        pack = get_pack(lang)
        chosen = self._line_ends(text, pack)
        if not chosen:
            raise NoCandidateWord(
                self.id,
                "the source has no non-blank line to read a line end from — "
                "try a source with at least one line of text",
            )
        return " ".join(chosen)
