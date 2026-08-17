"""Paragram — one letter changed, and the change made the point."""

from __future__ import annotations

import string
from itertools import combinations
from typing import Any

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams, require_capability
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang.base import WORDS


class ParagramParams(DiacriticParams):
    minimum: int = Field(default=1, ge=0, description="How many swapped pairs are wanted.")


def differ_by_one(left: str, right: str) -> bool:
    """Equal length, differing at exactly one position."""
    if len(left) != len(right) or left == right:
        return False
    return sum(a != b for a, b in zip(left, right, strict=True)) == 1


@register
class Paragram(BaseProcedure[ParagramParams]):
    """The swap is in the text, so the text alone decides.

    The row is `checkability: self` and requires no lexicon, so what can be
    verified is that both halves of the alteration are present — two words of a
    length, differing in one place. Whether the swap is witty is not a question
    code answers.
    """

    id = "paragram"

    @classmethod
    def params_model(cls) -> type[ParagramParams]:
        return ParagramParams

    def _normalise(self, text: str, pack: LanguagePack, fold: bool) -> list[str]:
        words = []
        for _, word in word_spans(text, pack):
            letters = "".join(
                pack.fold_diacritics(ch) if fold else ch.lower() for ch in word if ch.isalpha()
            )
            if letters:
                words.append(letters.lower())
        return words

    def _check(self, text: str, pack: LanguagePack, params: ParagramParams) -> Report:
        words = self._normalise(text, pack, params.fold_diacritics)
        pairs = [
            (left, right)
            for left, right in combinations(sorted(set(words)), 2)
            if differ_by_one(left, right)
        ]
        violations: list[Violation] = []
        if len(pairs) < params.minimum:
            violations.append(
                Violation(
                    rule="no_paragram",
                    offset=None,
                    found=f"{len(pairs)} swapped pairs",
                    expected=f"at least {params.minimum}",
                )
            )
        return self._report(
            good=min(len(pairs), params.minimum),
            total=params.minimum,
            violations=violations,
            metrics={"pairs": float(len(pairs))},
        )

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """Change one letter of a word in `text` into another word the lexicon knows.

        The original word is left in place and the swapped word is inserted
        right after it, so both halves of the pair survive into the output —
        `check` finds its pair by comparing words already in the text, and a
        generator that replaced the original in place would leave nothing for
        it to compare against.

        `lexicon.words` is required here but deliberately not added to the
        catalogue row: `requires` gates `check` too, and this row has always
        been checkable with core alone. ADR 0002 makes `apply` the optional
        half, so the generator carries its own requirement — the same
        arrangement `anagram` uses.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        require_capability(pack, WORDS, self.id)
        self.parse_params(params)

        for offset, word in word_spans(text, pack):
            if not word.isalpha():
                continue
            lowered = word.lower()
            for position in range(len(word)):
                for letter in string.ascii_lowercase:
                    if letter == lowered[position]:
                        continue
                    swapped = lowered[:position] + letter + lowered[position + 1 :]
                    if pack.is_word(swapped):
                        insert_at = offset + len(word)
                        return text[:insert_at] + " " + swapped + text[insert_at:]
        raise NoCandidateWord(self.id)
