"""Comparisons between a text and the source it was made from.

Four callers in the catalogue backlog need the same three shapes — a class of letters
preserved, a selection drawn out, a set of parts rearranged — so they live here rather
than in whichever procedure happened to need them first. `form_report` is the
precedent: it was extracted from real sonnets, not designed ahead of them.

`letter_class_report` follows that precedent on a smaller scale. `homoconsonantism`
was written first, by hand, with the comparison inline and no `keep` parameter at all
— it only ever asked "is this letter a consonant?". Writing `homovocalism` against
that code showed the entire body was identical except for one predicate (`not in
vowels` vs. `in vowels`) and one violation name (`wrong_consonant` vs. `wrong_vowel`).
Nothing else moved: not the index-by-index matching, not the `extra_letters` handling,
not the `max(len(expected), len(actual), 1)` denominator that keeps an empty source
from scoring as vacuously satisfied. That is why `keep` is a two-value `Literal`
rather than a predicate callback — a callback would have let a future caller ask for
some third partition of the alphabet this module was never asked to support, and the
two rows that exist do not need one.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

from denckring.core.protocol import LanguagePack, Violation
from denckring.core.text import letter_spans, word_spans

LetterClass = Literal["consonants", "vowels"]


class ClassResult(NamedTuple):
    violations: list[Violation]
    good: int
    total: int


def _of_class(
    text: str, pack: LanguagePack, keep: LetterClass, *, fold: bool
) -> list[tuple[int, str]]:
    # `pack.vowels()` rather than a literal "aeiou": German's vowel set is not
    # English's, and this helper is shared by rows that will later declare `de`.
    vowels = pack.vowels()
    wanted_vowels = keep == "vowels"
    return [
        (offset, letter)
        for offset, letter in letter_spans(text, pack, fold=fold)
        if (letter.casefold() in vowels) == wanted_vowels
    ]


def letter_class_report(
    text: str, source: str, pack: LanguagePack, *, keep: LetterClass, fold: bool
) -> ClassResult:
    """Whether `text` preserves the source's letters of class `keep`, in order.

    The violation names the letter rather than its index, because the letter is what a
    writer can act on — the same reasoning the metre scanner names the word.
    """
    rule = "wrong_consonant" if keep == "consonants" else "wrong_vowel"
    expected = _of_class(source, pack, keep, fold=fold)
    actual = _of_class(text, pack, keep, fold=fold)
    violations: list[Violation] = []
    good = 0
    for index, (_, letter) in enumerate(expected):
        if index < len(actual) and actual[index][1].casefold() == letter.casefold():
            good += 1
        else:
            violations.append(
                Violation(
                    rule=rule,
                    offset=actual[index][0] if index < len(actual) else None,
                    found=actual[index][1] if index < len(actual) else "",
                    expected=letter,
                )
            )
    if len(actual) > len(expected):
        violations.append(
            Violation(
                rule="extra_letters",
                offset=actual[len(expected)][0],
                found="".join(letter for _, letter in actual[len(expected) :]),
                expected="",
            )
        )
    # No `, 1` floor: when neither the source nor the text has a single letter of
    # `keep`'s class, `total` is genuinely 0, and `_report` already treats that as
    # vacuously satisfied — the same rule `lipogram` relies on for an empty text. A
    # floor here would score that case 0/1 with zero violations to explain why.
    return ClassResult(violations, good, max(len(expected), len(actual)))


def selection_report(chosen: list[str], source: str, pack: LanguagePack) -> ClassResult:
    """Whether every chosen word is drawn from the source, in the source's order.

    Order matters: a selection that reorders the source is a different procedure.
    The rule deciding *which* word to choose stays in the caller — `diastic` matches
    a seed's letters positionally, `mesostic` requires a spine letter inside the
    line — that is the only part the two selection rows do not share. Extracted from
    `diastic`, written by hand first with this loop inline: see that row's history
    for what the hand-written version taught about the signature (`chosen` is a
    plain list of words, not a `(text, params)` pair, because the caller has
    already tokenised its own candidate list, by word for `diastic` and by line's
    words for `mesostic`, before either can even ask whether it is in the source).

    Unlike `letter_class_report`, this floors `total` at 1 even when `chosen` is
    empty: an empty selection is not vacuously a reading of anything, so it scores
    0 rather than trivially satisfying the check. A generator that cannot find a
    single matching word raises rather than returning empty text for exactly this
    reason — see `diastic.apply`.
    """
    available = [word.casefold() for _, word in word_spans(source, pack)]
    violations: list[Violation] = []
    good = 0
    cursor = 0
    for word in chosen:
        folded = word.casefold()
        try:
            cursor = available.index(folded, cursor) + 1
        except ValueError:
            violations.append(
                Violation(
                    rule="not_in_source",
                    offset=None,
                    found=word,
                    expected="a word from the source, after the previous one",
                )
            )
            continue
        good += 1
    return ClassResult(violations, good, max(len(chosen), 1))
