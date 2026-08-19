"""Spoonerism — initial sounds exchanged between two words.

*The Lord is a shoving leopard* swaps "l" for "sh" between "loving" and
"shepherd". The catalogue row requires `[tokens, alphabet, phonemes]` —
deliberately without `lexicon.words` — because what
makes an exchange a spoonerism is that the two words' *initial sounds* differ, not
that the swap happens to land on other dictionary words. Comparing initial
letters would get this wrong in both directions: "knight" and "night" share no
initial letter but the same initial sound, and "phone" and "gnome" share no
initial letter either despite starting on different sounds for a different
reason. Comparing initial phoneme clusters (onsets) is what `pack.phonemes` buys
that spelling cannot, and it is the entire reason this row declares it.

`fold_diacritics` was dropped as unreached — nothing here folds. `alphabet` was
added because something here does call it: `_letter_onset` asks `pack.vowels()`
where the written onset ends, which is the same call `supervocalic` declares
`alphabet` for.

`pack.phonemes` raises `MissingCapability` for a word the pronouncing dictionary
does not carry (see `assonance_constraint`, ruling R14). Unlike a scan that can
fall back to other words in the same line, a pair here has nothing else to fall
back on — an unresolvable onset means the pair's genuineness cannot be verified
at all, so it is scored as a violation rather than silently dropped, keeping an
all-unresolvable text from vacuously scoring 1.0.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from denckring.core.base import BaseProcedure, require_capability
from denckring.core.errors import MissingCapability, NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang.base import ALPHABET, PHONEMES


def _phoneme_onset(phonemes: list[str]) -> list[str]:
    """Every consonant phoneme before the first vowel.

    A CMU-style vowel phoneme carries a stress digit; a consonant does not,
    matching `assonance_constraint._vowels`'s test in reverse. A word with no
    vowel phoneme at all (an initialism CMUdict spells out consonant by
    consonant) has no onset/rest split to make, so the whole thing is the onset.
    """
    for index, phoneme in enumerate(phonemes):
        if phoneme[-1:].isdigit():
            return phonemes[:index]
    return list(phonemes)


def _onset_or_none(word: str, pack: LanguagePack) -> list[str] | None:
    """`_phoneme_onset`, or `None` if the word is absent from the pronouncing
    dictionary. Catches `MissingCapability` around the per-word lookup only —
    never the surrounding check — so one unresolvable word cannot take an
    exception past the row that is supposed to report on it.
    """
    try:
        phonemes = pack.phonemes(word)
    except MissingCapability:
        return None
    return _phoneme_onset(phonemes)


def _letter_onset(word: str, pack: LanguagePack) -> tuple[str, str]:
    """The written prefix up to the first vowel letter, and the rest.

    `check` verifies genuineness by phonemes, but nothing in this codebase turns
    a phoneme sequence back into spelling, so `apply` needs a written stand-in
    for the phonetic boundary it cannot reconstruct. The first vowel *letter*
    is that stand-in — the same honestly-labelled approximation
    `alliterative_verse` uses for the opposite substitution, sound standing in
    for spelling there and spelling standing in for sound here. A word with no
    vowel letter at all is entirely onset, rest empty.
    """
    vowels = pack.vowels()
    for index, ch in enumerate(word):
        if ch.casefold() in vowels:
            return word[:index], word[index:]
    return word, ""


class SpoonerismParams(BaseModel):
    pass


@register
class Spoonerism(BaseProcedure[SpoonerismParams]):
    """Constructive: `apply` performs the onset swap `check` verifies.

    `check` reads the text as a sequence of word pairs — words 1-2, 3-4, and so
    on — and each pair must carry genuinely different onsets, the property that
    makes swapping them produce a second reading rather than the same one back.
    A leftover unpaired final word is not scored either way: there is no
    partner to compare it against.
    """

    id = "spoonerism"

    @classmethod
    def params_model(cls) -> type[SpoonerismParams]:
        return SpoonerismParams

    def _check(self, text: str, pack: LanguagePack, params: SpoonerismParams) -> Report:
        spans = word_spans(text, pack)
        pairs = list(zip(spans[0::2], spans[1::2], strict=False))
        if not pairs:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="too_few_words",
                        offset=None,
                        found=f"{len(spans)} word(s)",
                        expected="at least two words, forming a pair",
                    )
                ],
                metrics={"pairs": 0.0, "estimated_words": 0.0},
            )
        violations: list[Violation] = []
        good = 0
        estimated = 0
        for (first_offset, first), (_, second) in pairs:
            first_onset = _onset_or_none(first, pack)
            second_onset = _onset_or_none(second, pack)
            if first_onset is None or second_onset is None:
                estimated += (first_onset is None) + (second_onset is None)
                violations.append(
                    Violation(
                        rule="unresolved_phonemes",
                        offset=first_offset,
                        found=f"{first!r}/{second!r}",
                        expected="both words in the pronouncing dictionary",
                    )
                )
                continue
            if first_onset == second_onset:
                violations.append(
                    Violation(
                        rule="onsets_not_distinct",
                        offset=first_offset,
                        found=f"{first!r}/{second!r} both start on {first_onset!r}",
                        expected="two words with differing initial phoneme clusters",
                    )
                )
                continue
            good += 1
        return self._report(
            good=good,
            total=len(pairs),
            violations=violations,
            metrics={"pairs": float(len(pairs)), "estimated_words": float(estimated)},
        )

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """Swap the written onsets of the text's first two words.

        Only those two words survive into the output — anything else in `text`
        is discarded, not carried through. `check` reads the *whole* produced
        text as a sequence of pairs, so an unswapped remainder could add pairs
        of its own that `check` fails independently of anything this method
        did; dropping it is what keeps the round trip a property of this
        method alone.

        The written onset (`_letter_onset`) is a guess at where the spoken
        onset (`_onset_or_none`, what `check` actually compares) ends, and nothing
        here can force the guess right — spelling and pronunciation part ways
        too often for that. So the guess is verified before it is returned:
        both swapped spellings must resolve in the pronouncing dictionary to
        onsets that still differ, the same test `check` applies, computed the
        same way. When it fails — most often because a swapped spelling is not
        a dictionary word at all — `NoCandidateWord` is raised rather than
        handing back text `check` would reject; `check` floors a pairless or
        unresolved text's score below 1.0, so silently returning the guess
        would do exactly that.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        # `check` is gated by `BaseProcedure.check`; `apply` has no such template
        # method above it, so it guards its own capabilities the way `anagram` does.
        # Without this, a pack lacking `phonemes` reached `_onset_or_none`, whose
        # `except MissingCapability` is there to tolerate one unknown *word* and
        # silently swallowed a missing *capability* instead, turning a fixable
        # "install denckring[en]" into "no candidate word".
        require_capability(pack, PHONEMES, self.id)
        require_capability(pack, ALPHABET, self.id)
        self.parse_params(params)
        spans = word_spans(text, pack)
        if len(spans) < 2:
            raise NoCandidateWord(
                self.id,
                "needs at least two words to swap onsets between — try a "
                "two-word phrase, or check a text instead of generating one",
            )
        first, second = spans[0][1], spans[1][1]
        first_onset, first_rest = _letter_onset(first, pack)
        second_onset, second_rest = _letter_onset(second, pack)
        swapped_first = second_onset + first_rest
        swapped_second = first_onset + second_rest
        resolved_first = _onset_or_none(swapped_first, pack)
        resolved_second = _onset_or_none(swapped_second, pack)
        if resolved_first is None or resolved_second is None or resolved_first == resolved_second:
            raise NoCandidateWord(
                self.id,
                f"swapping the written onsets of {first!r} and {second!r} does not "
                "produce two words the pronouncing dictionary resolves to distinct "
                "initial sounds — try two words whose spelling and pronunciation "
                "agree on where the onset ends, or check a text instead of "
                "generating one",
            )
        return f"{swapped_first} {swapped_second}"
