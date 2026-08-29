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

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import selection_report
from denckring.core.text import line_spans, word_spans


class MesosticParams(SourceParams):
    # Defaulted like `every_nth_word.n`, so `apply()` is usable with no extra
    # keyword — unlike `diastic.seed_phrase`, `spine` was never forced into a
    # rename by a reserved-keyword collision, so there was no forced reason
    # for a default; it is here purely for that zero-argument convenience.
    spine: str = Field(default="the", description="The spine word read down the lines.")


class MesosticApplyParams(MesosticParams, ApplyParams):
    pass


@register
class Mesostic(ConstructiveProcedure[MesosticParams, MesosticApplyParams]):
    """Constructive: `apply` arranges the lines that `check` verifies."""

    id = "mesostic"

    @classmethod
    def params_model(cls) -> type[MesosticParams]:
        return MesosticParams

    def _check(self, text: str, pack: LanguagePack, params: MesosticParams) -> Report:
        lines = line_spans(text)
        # Word offsets are relative to their own line, so each is shifted by the
        # line's own offset to give a position in the whole text — which is what
        # every other row's violations report.
        chosen = [
            (line_offset + offset, word)
            for line_offset, line in lines
            for offset, word in word_spans(line, pack)
        ]
        result = selection_report(chosen, params.source, pack)
        violations = list(result.violations)
        good = result.good
        total = result.total
        letters = [ch for ch in params.spine.casefold() if ch.isalpha()]
        for index, (offset, line) in enumerate(lines[: len(letters)]):
            total += 1
            letter = letters[index]
            if letter in line.casefold():
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="spine_letter_missing",
                        offset=offset,
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

    @classmethod
    def apply_params_model(cls) -> type[MesosticApplyParams]:
        return MesosticApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: MesosticApplyParams) -> Produced:
        """Read through `text`, which serves as the source, one word per line.

        Each line is a single word carrying that line's spine letter somewhere in
        it — sufficient, since `_check` only asks whether the letter is *in* the
        line, not at a fixed position. Stops rather than skipping a letter that
        finds no candidate, for the same round-trip reason as `diastic.apply`, and
        raises `NoCandidateWord` instead of returning empty text if even the first
        letter finds nothing to read.
        """
        words = [word for _, word in word_spans(text, pack)]
        letters = [ch for ch in params.spine.casefold() if ch.isalpha()]
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
            raise NoCandidateWord(
                self.id,
                "no word in the source carries the spine's first letter — try "
                "a different source or spine, or check a text instead of "
                "generating one",
            )
        return plain(["\n".join(chosen)])
