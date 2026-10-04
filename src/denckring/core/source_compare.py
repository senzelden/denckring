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
Nothing else moved: not the matching, not the `extra_letters` handling, not the
denominator that keeps an empty source from scoring as vacuously satisfied. (The
matching was index by index then; it is an alignment now, `aligned_report`, shared
with every positional row, ADR 0056.) That is why `keep` is a two-value `Literal`
rather than a predicate callback — a callback would have let a future caller ask for
some third partition of the alphabet this module was never asked to support, and the
two rows that exist do not need one.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from typing import Literal, NamedTuple

from denckring.core.protocol import LanguagePack, Violation
from denckring.core.text import letter_spans, word_spans

LetterClass = Literal["consonants", "vowels"]


def unchanged(
    text: str,
    source: str,
    pack: LanguagePack,
    *,
    allow: bool,
    alternative: Callable[[], bool],
    fold: bool = True,
) -> list[Violation]:
    """`[unchanged]` when `allow` is false, `text` is `source` itself, and the
    source admits a different correct answer; else `[]`.

    `alternative` is each row's own answer to the last clause (ruling R-U2a). A
    one-sentence `recombination` or a one-word `cut_up` has no answer but the
    copy, and refusing it there would make the instance unsatisfiable rather than
    catch a trivial pass. Called only when the rest already holds, so a row pays
    for its predicate only on a refused copy. Required, not defaulted, so a new
    caller has to say what its rule leaves open.

    A copy is the source's letters in the source's order, so case, spacing and
    punctuation do not make a text new — the comparison `antigram` makes. Its
    rule name is kept, and its wording but for "rearrangement", which is
    antigram's alone. A list, so a caller adds its length to the
    total and the copy costs one unit of score: `_report` reads a score of 1.0 as
    satisfied, and a violation must never sit beside one.

    `fold` is the row's own `fold_diacritics` where it has one. A row without it
    compares words casefolded only, and passes `fold=False` to match.
    """
    if allow:
        return []
    if not is_copy(text, source, pack, fold=fold):
        return []
    if not alternative():
        return []
    return [
        Violation(
            rule="unchanged",
            offset=None,
            found=text.strip(),
            expected="a change to the source, not the source itself",
        )
    ]


def is_copy(text: str, source: str, pack: LanguagePack, *, fold: bool) -> bool:
    """Whether `text` is `source`'s letters in `source`'s order: what `unchanged`
    refuses, and what `ConstructiveProcedure`'s guard refuses from a generator
    whose checker can refuse it, so the two cannot disagree about a copy."""
    return [ch for _, ch in letter_spans(text, pack, fold=fold)] == [
        ch for _, ch in letter_spans(source, pack, fold=fold)
    ]


def several_words(source: str, pack: LanguagePack) -> bool:
    """The `alternative` of the rows whose answer is a selection of the source's
    words (`cut_up`, `melting_text`, `diastic`, `mesostic`).

    One word of a passing copy, alone, is a different answer on each, and needs a
    second word to leave out: any word for `cut_up` and `melting_text`; for
    `diastic` the first, which carries the seed's first letter where the copy
    did; for `mesostic` the word of the copy's first line that carries the
    spine's first letter, as a line of its own (only as many lines as the text
    has are checked). An empty text is no alternative: it is the
    degenerate output `apply` refuses, whatever some checkers score it.
    """
    return len(word_spans(source, pack)) >= 2


class ClassResult(NamedTuple):
    violations: list[Violation]
    good: int
    total: int


Step = Literal["match", "substitute", "insert", "delete"]


class Aligned(NamedTuple):
    """One step of an alignment: `expected` and `actual` index the two sequences,
    and the side a step has no unit on is `None` (an insertion has no expected
    unit, a deletion no actual one)."""

    step: Step
    expected: int | None
    actual: int | None


def align(expected: Sequence[str], actual: Sequence[str]) -> list[Aligned]:
    """The steps that turn `expected` into `actual`, in order (ADR 0056).

    The positional rows compared index by index, so one dropped unit shifted every
    later one and the text scored as if it had nothing right after the drop. This
    is a minimal-edit (Levenshtein) alignment instead (ruling R-U8b): a
    substitution, an insertion and a deletion each cost 1, a match 0, and the
    steps are the cheapest way from one sequence to the other. Traced back from
    the end, a tie prefers the diagonal (a match or a substitution), then a
    deletion, then an insertion, so the same pair always aligns the same way, and
    a lone substitution stays one substituted unit, scoring exactly what index
    by index scored. `difflib.SequenceMatcher` was the first choice and was
    dropped: it keeps the longest matching block first, so a substitution beside
    an identical unit came out as an insertion and a deletion.

    Only identical sequences align with no step but `match`, so a score of 1.0
    still means an exact match and nothing else (ADR 0005). The table is
    O(n·m) in time and memory.
    """
    rows, cols = len(expected), len(actual)
    # cost[i][j]: the fewest edits turning expected[:i] into actual[:j].
    cost = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows + 1):
        cost[i][0] = i
    for j in range(cols + 1):
        cost[0][j] = j
    for i in range(1, rows + 1):
        above, here = cost[i - 1], cost[i]
        want = expected[i - 1]
        for j in range(1, cols + 1):
            here[j] = min(
                above[j - 1] + (want != actual[j - 1]),
                above[j] + 1,
                here[j - 1] + 1,
            )
    steps: list[Aligned] = []
    i, j = rows, cols
    while i or j:
        if i and j and cost[i][j] == cost[i - 1][j - 1] + (expected[i - 1] != actual[j - 1]):
            same = expected[i - 1] == actual[j - 1]
            steps.append(Aligned("match" if same else "substitute", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and cost[i][j] == cost[i - 1][j] + 1:
            steps.append(Aligned("delete", i - 1, None))
            i -= 1
        else:
            steps.append(Aligned("insert", None, j - 1))
            j -= 1
    steps.reverse()
    return steps


def gaps(
    steps: Sequence[Aligned],
    expected: Sequence[str],
    actual: Sequence[tuple[int, str]],
    *,
    inserted: str,
    deleted: str,
    joiner: str,
    end: int,
    note: Callable[[int, str], str] | None = None,
) -> dict[int, Violation]:
    """The insertions and deletions of an alignment, keyed by the step each is
    reported at, so a caller judging the paired units its own way (N+7) can
    keep every violation in text order.

    A run of inserted units is one `inserted` violation at its first unit, its
    units joined by `joiner`: the shape every `extra_*` rule had when only a
    tail could be surplus. A deleted unit is one `deleted` violation each, as
    `homosyntaxism`'s `missing_word` reports each position the writer still
    owes, placed where it would go: at the next unit of the text, or at `end`
    (the text's length) when none follows. `note`, given the expected index and
    unit, phrases a deletion.
    """
    found: dict[int, Violation] = {}
    upcoming: int | None = None
    for index in range(len(steps) - 1, -1, -1):
        _, i, j = steps[index]
        if j is not None:
            upcoming = j
            continue
        if i is not None:
            found[index] = Violation(
                rule=deleted,
                offset=actual[upcoming][0] if upcoming is not None else end,
                found="",
                expected=expected[i],
                note=note(i, expected[i]) if note is not None else None,
            )
    runs: dict[int, list[int]] = {}
    start: int | None = None
    for index, (step, _, j) in enumerate(steps):
        if step == "insert" and j is not None:
            start = index if start is None else start
            runs.setdefault(start, []).append(j)
        else:
            start = None
    for index, members in runs.items():
        found[index] = Violation(
            rule=inserted,
            offset=actual[members[0]][0],
            found=joiner.join(actual[j][1] for j in members),
            expected="",
        )
    return dict(sorted(found.items()))


def aligned_report(
    expected: Sequence[str],
    actual: Sequence[tuple[int, str]],
    *,
    key: Callable[[str], str],
    substituted: str,
    inserted: str,
    deleted: str,
    joiner: str,
    end: int,
    note: Callable[[int, str], str] | None = None,
) -> ClassResult:
    """Score `actual` against `expected` over their alignment (`align`, ADR 0056).

    The one comparison every positional row makes: `positional_report`,
    `letter_class_report`, `slenderizing` and `every_nth_word` call it, and
    N+7's word-count mismatch uses `align` and `gaps` directly. `good` is the
    matched count and `total` the alignment's length, so one dropped unit costs
    one unit rather than every unit after it.

    `key` is what two units are compared by (casefolded words, or letters as
    the row folds them); `found` and `expected` keep each unit as shown. A
    substitution keeps the row's rule (`substituted`); insertions and deletions
    are `gaps`'. `note`, given the expected index and unit, phrases a
    substitution or a deletion.
    """
    steps = align([key(unit) for unit in expected], [key(unit) for _, unit in actual])
    unpaired = gaps(
        steps,
        expected,
        actual,
        inserted=inserted,
        deleted=deleted,
        joiner=joiner,
        end=end,
        note=note,
    )
    violations: list[Violation] = []
    good = 0
    for index, (step, i, j) in enumerate(steps):
        if index in unpaired:
            violations.append(unpaired[index])
        elif step == "match":
            good += 1
        elif step == "substitute" and i is not None and j is not None:
            offset, unit = actual[j]
            violations.append(
                Violation(
                    rule=substituted,
                    offset=offset,
                    found=unit,
                    expected=expected[i],
                    note=note(i, expected[i]) if note is not None else None,
                )
            )
    return ClassResult(violations, good, len(steps))


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
    # Aligned, not compared index by index (ADR 0056): one dropped letter costs
    # one unit. Its `total` is the alignment's length, with no `, 1` floor: when
    # neither the source nor the text has a single letter of `keep`'s class,
    # `total` is genuinely 0, and `_report` already treats that as vacuously
    # satisfied — the same rule `lipogram` relies on for an empty text. A floor
    # here would score that case 0/1 with zero violations to explain why.
    return aligned_report(
        [letter for _, letter in _of_class(source, pack, keep, fold=fold)],
        _of_class(text, pack, keep, fold=fold),
        key=str.casefold,
        substituted=rule,
        inserted="extra_letters",
        deleted="missing_letter",
        joiner="",
        end=len(text),
    )


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
    end: int,
) -> ClassResult:
    """Whether `chosen` is exactly the words the source's positional rule produces.

    `end` is the checked text's length: a missing word no later word of the text
    follows is placed there, at the end where it would go, as `every_nth_word`
    and `slenderizing` place theirs (`Violation.offset`).

    The fourth shape, and a sibling of `selection_report` rather than a variant of
    it: that one asks only whether each chosen word occurs in the source in order,
    which every selection row needs; this asks whether the chosen word is the
    *particular* word the rule names for that position, which `column_reading` and
    `haikuization` both need and the two `diastic`-family rows do not — their rule
    is a property of the word (a letter at an index), not an identity fixed in
    advance. Those two rows carried this loop, the `extra_words` tail and all,
    line for line identical but for the rule name and how `expected` was computed
    (the loop is `aligned_report` now, ADR 0056) — the second of which is
    exactly the caller's business, and is why `expected` arrives already computed.

    `note` is a callable where `letter_class_report`'s `keep` is a `Literal`, and
    the difference is deliberate rather than inconsistent: `keep` decides the
    verdict, so leaving it open would let a caller ask for a partition this module
    never agreed to support, while `note` only phrases a violation a human reads
    and cannot change whether the text passes.
    """
    # Aligned (ADR 0056), so a dropped word costs one unit and the words after
    # it still count. Each surplus word is one more unit of the alignment, so a
    # text with source words appended cannot pass beside its own `extra_words`
    # violation, as `column_reading` once did (R-F1).
    return aligned_report(
        expected,
        chosen,
        key=str.casefold,
        substituted=rule,
        inserted="extra_words",
        deleted="missing_word",
        joiner=" ",
        end=end,
        note=note,
    )
