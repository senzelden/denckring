"""Mesostic — a spine word runs down the middle of the lines rather than the margin.

John Cage's method. Built on the same two rules as `diastic`: the words come from the
source in order (`selection_report`, shared with that row), and each line carries the
spine's letter — but *inside* the line rather than at a fixed index, since a mesostic's
spine letter is conventionally the emphasised one wherever it falls, not a position an
acrostic-style scan would find. `diastic` matches a seed's letters positionally against
single words; this row matches a spine's letters against whole lines. That difference
is exactly what stayed out of `selection_report`.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import selection_report
from denckring.core.text import line_spans, word_spans


class MesosticParams(SourceParams):
    # Defaulted like `every_nth_word.n`, so `apply()` is usable with no extra
    # keyword — unlike `diastic.seed_phrase`, `spine` has no reserved-name
    # collision with the `Constructive` protocol's `seed: int | None`, so there
    # was no forced reason for a default; it is here purely for that
    # zero-argument convenience.
    spine: str = Field(default="the", description="The spine word read down the lines.")


@register
class Mesostic(BaseProcedure[MesosticParams]):
    """Constructive: `apply` arranges the lines that `check` verifies."""

    id = "mesostic"

    @classmethod
    def params_model(cls) -> type[MesosticParams]:
        return MesosticParams

    def _check(self, text: str, pack: LanguagePack, params: MesosticParams) -> Report:
        lines = [line for _, line in line_spans(text)]
        chosen = [word for line in lines for _, word in word_spans(line, pack)]
        result = selection_report(chosen, params.source, pack)
        violations = list(result.violations)
        good = result.good
        total = result.total
        letters = [ch for ch in params.spine.casefold() if ch.isalpha()]
        for index, line in enumerate(lines[: len(letters)]):
            total += 1
            letter = letters[index]
            if letter in line.casefold():
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="spine_letter_missing",
                        offset=None,
                        found=line,
                        expected=letter,
                        note=f"line {index + 1} must carry {letter!r}",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(len(lines))},
        )

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Read through `text`, which serves as the source, one word per line.

        Each line is a single word carrying that line's spine letter somewhere in
        it — sufficient, since `_check` only asks whether the letter is *in* the
        line, not at a fixed position. Stops rather than skipping a letter that
        finds no candidate, for the same round-trip reason as `diastic.apply`, and
        raises `NoCandidateWord` instead of returning empty text if even the first
        letter finds nothing to read.
        """
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        pack = get_pack(lang)
        words = [word for _, word in word_spans(text, pack)]
        letters = [ch for ch in parsed.spine.casefold() if ch.isalpha()]
        chosen: list[str] = []
        cursor = 0
        for letter in letters:
            match = None
            for position in range(cursor, len(words)):
                if letter in words[position].casefold():
                    match = position
                    break
            if match is None:
                break
            chosen.append(words[match])
            cursor = match + 1
        if not chosen:
            raise NoCandidateWord(self.id)
        return "\n".join(chosen)
