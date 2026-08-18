"""Diastic — words whose nth letter matches the nth letter of a seed phrase.

Jackson Mac Low's reading-through method. Two rules apply at once: the words come
from the source in order, and each carries the seed phrase's letter at its own
index. This row was written by hand first, with both rules inline and no helper —
see `denckring.core.source_compare.selection_report` for what that draft taught
about the order half, now extracted there and shared with `mesostic`. The
positional letter rule stays here: it is the one thing the two rows do not share.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import selection_report
from denckring.core.text import word_spans


class DiasticParams(SourceParams):
    # Named `seed_phrase`, not `seed`: the `Constructive` protocol reserves the
    # keyword `seed` on every `apply()` for an RNG seed (see `every_nth_word.py`).
    # A field named `seed` here would collide with that reserved parameter —
    # Python binds a keyword matching an explicit parameter name to that
    # parameter before any of it reaches `**params`, silently, so `apply(text,
    # seed="sil")` would discard `"sil"` and fall back to whatever default the
    # field carried, with no error to say so. `seed_phrase` sidesteps the
    # collision entirely and is the more accurate name besides: this is a
    # phrase, not an RNG seed. Defaulted for the same reason `every_nth_word.n`
    # is: it lets `apply()` be called with no extra keyword at all.
    seed_phrase: str = Field(
        default="the", description="The seed phrase whose letters drive the selection."
    )


@register
class Diastic(BaseProcedure[DiasticParams]):
    """Constructive: `apply` performs the reading-through that `check` verifies."""

    id = "diastic"

    @classmethod
    def params_model(cls) -> type[DiasticParams]:
        return DiasticParams

    def _check(self, text: str, pack: LanguagePack, params: DiasticParams) -> Report:
        chosen = [word for _, word in word_spans(text, pack)]
        result = selection_report(chosen, params.source, pack)
        violations = list(result.violations)
        good = result.good
        total = result.total
        letters = [ch for ch in params.seed_phrase.casefold() if ch.isalpha()]
        for index, word in enumerate(chosen):
            if index >= len(letters):
                break
            folded = word.casefold()
            total += 1
            letter = letters[index]
            if index < len(folded) and folded[index] == letter:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_letter_at_position",
                        offset=None,
                        found=folded[index] if index < len(folded) else "",
                        expected=letter,
                        note=f"position {index + 1} of {word!r}",
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
        """Read through `text`, which serves as the source, against the seed phrase.

        Stops as soon as a required letter cannot be found in the remaining source,
        rather than skipping it: `_check` matches word `i` of the *output* against
        `seed_phrase[i]`, so skipping a letter would misalign every word selected
        after the gap and break the round trip. Raises `NoCandidateWord` rather than
        returning an empty string when even the first letter finds no match:
        `_check` floors its denominator at 1, so an empty selection scores 0 rather
        than vacuously 1 — silently returning "" would hand back text its own
        checker rejects.
        """
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        pack = get_pack(lang)
        words = [word for _, word in word_spans(text, pack)]
        letters = [ch for ch in parsed.seed_phrase.casefold() if ch.isalpha()]
        chosen: list[str] = []
        cursor = 0
        for index, letter in enumerate(letters):
            match = None
            for position in range(cursor, len(words)):
                candidate = words[position].casefold()
                if index < len(candidate) and candidate[index] == letter:
                    match = position
                    break
            if match is None:
                break
            chosen.append(words[match])
            cursor = match + 1
        if not chosen:
            raise NoCandidateWord(self.id)
        return " ".join(chosen)
