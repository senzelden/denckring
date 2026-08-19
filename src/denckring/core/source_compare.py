"""Comparisons between a text and the source it was made from.

Ten callers in the catalogue backlog need the same four shapes — a class of letters
preserved, a selection drawn out, a positional rule reproduced, a set of parts
rearranged — so they live here rather than in whichever procedure happened to need
them first. `form_report` is the
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

from collections import Counter
from collections.abc import Callable
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


def selection_report(chosen: list[tuple[int, str]], source: str, pack: LanguagePack) -> ClassResult:
    """Whether every chosen word is drawn from the source, in the source's order.

    Order matters: a selection that reorders the source is a different procedure.
    The rule deciding *which* word to choose stays in the caller — `diastic` matches
    a seed's letters positionally, `mesostic` requires a spine letter inside the
    line — that is the only part the two selection rows do not share. Extracted from
    `diastic`, written by hand first with this loop inline: see that row's history
    for what the hand-written version taught about the signature (`chosen` is a
    flat list of words, not a `(text, params)` pair, because the caller has
    already tokenised its own candidate list, by word for `diastic` and by line's
    words for `mesostic`, before either can even ask whether it is in the source).

    `chosen` carries offsets rather than bare words. It took `list[str]`, which
    structurally forced `offset=None` on every `not_in_source` violation any caller
    could produce — while all four callers computed the offsets and threw them away
    in the same comprehension. `rearrangement_report` keeps `list[str]`: its
    `missing_part` violation names something *absent* from the text and so has no
    offset to give, and pairing that with an offset-bearing `invented_part` would
    be a wider change for half an answer.

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
    for offset, word in chosen:
        folded = word.casefold()
        try:
            cursor = available.index(folded, cursor) + 1
        except ValueError:
            violations.append(
                Violation(
                    rule="not_in_source",
                    offset=offset,
                    found=word,
                    expected="a word from the source, after the previous one",
                )
            )
            continue
        good += 1
    return ClassResult(violations, good, max(len(chosen), 1))


def rearrangement_report(parts: list[str], source_parts: list[str]) -> ClassResult:
    """Whether `parts` is exactly `source_parts` reordered — nothing added or lost.

    Checked as a multiset rather than a set: a procedure that drops one of two
    identical lines has changed the text, and a set comparison would not notice. The
    rule producing the *order* stays in the caller — `boustrophedon` reverses
    alternate parts in place, `text_folding` swaps the two flaps either side of a
    fold — that is the only part the two rows do not share.

    `boustrophedon` was written first, by hand, with this comparison inline: see
    that row's history for what the draft taught. Two things did not survive
    unchanged from a first, more literal reading of "compare the multisets": no
    `, 1` floor on `total`, and `good` as the multiset intersection rather than
    `total` minus what is missing. Both were needed for the same test —
    `test_a_rearrangement_may_not_invent_material` — which a version scored
    satisfied even though it carried an `invented_part` violation, because pinning
    `total` to `sum(want.values())` alone let an extra part in `have` cost nothing
    against the score. Comparing intersection sizes instead fixes that, and drops
    the floor along with it: an all-blank `parts` and `source_parts` then leaves
    `total == 0`, which `_report` already scores vacuously satisfied — the same
    reasoning `letter_class_report` documents for skipping the floor `selection_report`
    keeps.
    """
    have = Counter(part.strip().casefold() for part in parts)
    want = Counter(part.strip().casefold() for part in source_parts)
    violations: list[Violation] = []
    for part, count in (want - have).items():
        violations.append(
            Violation(rule="missing_part", offset=None, found="", expected=part, note=f"x{count}")
        )
    for part, count in (have - want).items():
        violations.append(
            Violation(rule="invented_part", offset=None, found=part, expected="", note=f"x{count}")
        )
    good = sum((want & have).values())
    total = max(sum(want.values()), sum(have.values()))
    return ClassResult(violations, good, total)


def positional_report(
    chosen: list[tuple[int, str]],
    expected: list[str],
    *,
    rule: str,
    note: Callable[[int, str], str],
) -> ClassResult:
    """Whether `chosen` is exactly the words the source's positional rule produces.

    The fourth shape, and a sibling of `selection_report` rather than a variant of
    it: that one asks only whether each chosen word occurs in the source in order,
    which every selection row needs; this asks whether the chosen word is the
    *particular* word the rule names for that position, which `column_reading` and
    `haikuization` both need and the two `diastic`-family rows do not — their rule
    is a property of the word (a letter at an index), not an identity fixed in
    advance. Those two rows carried this loop, the `extra_words` tail and all,
    line for line identical but for the rule name and how `expected` was computed
    — the second of which is exactly the caller's business, and is why `expected`
    arrives already computed.

    `note` is a callable where `letter_class_report`'s `keep` is a `Literal`, and
    the difference is deliberate rather than inconsistent: `keep` decides the
    verdict, so leaving it open would let a caller ask for a partition this module
    never agreed to support, while `note` only phrases a violation a human reads
    and cannot change whether the text passes.
    """
    violations: list[Violation] = []
    good = 0
    for index, word in enumerate(expected):
        if index < len(chosen) and chosen[index][1].casefold() == word.casefold():
            good += 1
        else:
            violations.append(
                Violation(
                    rule=rule,
                    offset=chosen[index][0] if index < len(chosen) else None,
                    found=chosen[index][1] if index < len(chosen) else "",
                    expected=word,
                    note=note(index, word),
                )
            )
    if len(chosen) > len(expected):
        violations.append(
            Violation(
                rule="extra_words",
                offset=chosen[len(expected)][0],
                found=" ".join(word for _, word in chosen[len(expected) :]),
                expected="",
            )
        )
    return ClassResult(violations, good, len(expected))
