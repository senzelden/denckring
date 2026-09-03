"""N+7 — every noun replaced by the seventh noun after it in the dictionary."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import Field, field_validator

from denckring.core.base import (
    ApplyParams,
    BaseProcedure,
    ConstructiveProcedure,
    SourceParams,
    plain,
)
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


def resolve_dictionary(
    pack: LanguagePack, dictionary: list[str] | None
) -> tuple[Sequence[str], Callable[[str], int | None]]:
    """The list to walk and the way to find a word in it.

    Two returns rather than one because the pack's own lookup does more than a
    dict get — `noun_index` lemmatises — and a supplied list has no lemmatiser
    behind it. Casefolded matching is the most a bare list can honestly offer,
    and matches how `displacement_report` already compares words.
    """
    if dictionary is None:
        return pack.nouns(), pack.noun_index
    entries = tuple(dictionary)
    positions = {word.casefold(): index for index, word in enumerate(entries)}
    return entries, lambda word: positions.get(word.casefold())


#: A straight apostrophe and its typographic cousin. French elides a proclitic
#: onto the following word with either.
_ELISION_MARKS = ("'", "\u2019")


def split_elision(word: str) -> tuple[str, str]:
    """(proclitic-with-apostrophe or `""`, the rest).

    The tokeniser keeps an apostrophe-bearing token whole -- `l'île`,
    `d'espoir` -- because 94 real French words carry an internal apostrophe
    of their own (`aujourd'hui`), and splitting every apostrophe
    unconditionally would misread those. No noun does, though, so a leading
    `proclitic'` before a noun is always an elision boundary, never part of
    the noun itself, which is what makes it safe to always split here rather
    than trying the whole word against the noun index first the way
    `denckring_fr_data._table_entry` tries a whole form before falling back
    (that helper's table DOES hold apostrophe-bearing entries; the noun list
    does not, checked against the shipped lexicon).

    Splits at the LAST mark, the same as `_table_entry`, for a chained
    elision. Language-blind: no English or German word carries an
    apostrophe, so this is a silent no-op there, and every one of the words
    it splits stays a single call site (`displace`, `displacement_report`)
    rather than a difference in `noun_index` between languages.
    """
    for mark in _ELISION_MARKS:
        if mark in word:
            prefix, _, tail = word.rpartition(mark)
            return prefix + mark, tail
    return "", word


def displace(
    text: str,
    pack: LanguagePack,
    nouns: Sequence[str],
    noun_index: Callable[[str], int | None],
    offset: int,
) -> str:
    """Replace each word the noun list knows with the one `offset` further on.

    Word spans are substituted in place rather than re-joined, so punctuation
    and spacing survive — `displacement_report` compares position by position,
    and a generator that normalised the whitespace would produce text its own
    checker then rejected for the wrong reason.

    `nouns` and `noun_index` are the resolved pair from `resolve_dictionary`,
    passed in rather than re-resolved here: two call sites resolving
    independently is how they come to disagree about which list was walked.

    `split_elision` isolates a leading proclitic first, so a token like
    `l'île` displaces only `île` and keeps `l'` untouched. The proclitic is
    reattached exactly as written -- not re-elided against the new noun's
    initial sound -- because choosing `l'`/`le`/`la`/`de`/`d'` correctly
    needs the noun's grammatical gender, which the noun list does not carry.
    A displacement landing on a consonant-initial noun therefore keeps a
    vowel-elided proclitic literally; that is a known, honest limitation
    pinned by a test, not a defect this generator tries to paper over.
    """
    pieces: list[str] = []
    cursor = 0
    for offset_in_text, word in word_spans(text, pack):
        prefix, tail = split_elision(word)
        index = noun_index(tail)
        if index is None:
            continue
        pieces.append(text[cursor:offset_in_text])
        pieces.append(prefix)
        pieces.append(nouns[(index + offset) % len(nouns)])
        cursor = offset_in_text + len(word)
    pieces.append(text[cursor:])
    return "".join(pieces)


class NPlus7Params(SourceParams):
    offset: int = Field(default=7, description="How many nouns to count forward.")
    dictionary: list[str] | None = Field(
        default=None,
        description=(
            "The ordered word list to displace within. Defaults to the pack's "
            "nouns. Order is the contract: N+7 walks the seventh entry after a "
            "word, so a supplied list's order is the caller's editorial choice."
        ),
    )
    # A supplied dictionary works wherever the pack already has a noun list; it
    # does not unlock N+7 for a language whose pack has none, because the spine
    # checks capabilities before it parses parameters. Making the capability
    # conditional on a parameter inverts two steps every procedure inherits and
    # is out of scope here.

    # `RhymeParams.unknown_rhyme` (base.py) solves this exact shape for a
    # different undecidable — a word list cannot say whether *run* was left
    # alone because it is a noun that survived, or because it is a verb here.
    # Same three readings, same names, for the same reason: a caller who has
    # met one has met both.
    ambiguous_nouns: Literal["undecidable", "free", "strict"] = Field(
        default="free",
        description=(
            "What an unchanged word that the dictionary lists means: leave the "
            "position unscored (undecidable), accept it (free), or fail it "
            "(strict)."
        ),
    )

    @field_validator("dictionary")
    @classmethod
    def _entries_survive_the_tokeniser(cls, value: list[str] | None) -> list[str] | None:
        # ADR 0015's rule for `nouns()`, applied to a supplied list for the same
        # reason: a displacement has to come back from the tokeniser whole, and
        # `(index + offset) % len(...)` needs something to divide by.
        if value is None:
            return None
        if not value:
            raise ValueError("dictionary must not be empty")
        bad = [word for word in value if not word.isalpha()]
        if bad:
            raise ValueError(f"dictionary entries must be single alphabetic words: {bad[:3]}")
        return value


class NPlus7ApplyParams(NPlus7Params, ApplyParams):
    pass


def displacement_report(
    procedure: BaseProcedure[NPlus7Params],
    text: str,
    pack: LanguagePack,
    params: NPlus7Params,
) -> Report:
    """Check a noun-displacement of a source, tolerating part-of-speech ambiguity.

    A word list cannot tell you that *run* is a verb in this sentence. So an
    unchanged word that happens to be in the noun list is never automatically a
    mistake; what it counts as instead is `params.ambiguous_nouns`'s call —
    accepted (`free`, the default, and what shipped before this parameter
    existed), left out of the score entirely (`undecidable`), or failed
    (`strict`). Every reading reports the same `ambiguous_words` count, in the
    same way `estimated_words` keeps the syllable heuristic honest — only what
    the count does to the score changes.
    """
    candidate = word_spans(text, pack)
    source = word_spans(params.source, pack)
    nouns, noun_index = resolve_dictionary(pack, params.dictionary)
    violations: list[Violation] = []

    if len(candidate) != len(source):
        return procedure._report(
            good=0,
            total=1,
            violations=[
                Violation(
                    rule="wrong_word_count",
                    offset=None,
                    found=f"{len(candidate)} words",
                    expected=f"{len(source)} words",
                )
            ],
            metrics={"words": float(len(candidate)), "ambiguous_words": 0.0},
        )

    ambiguous = 0
    undecided = 0
    good = 0
    for (offset, produced), (_, original) in zip(candidate, source, strict=True):
        # A leading proclitic glued on by elision (`l'`, `d'`, `qu'`) is
        # never itself a noun, so it is compared separately and must not
        # change; the noun index and every reading below runs on the tail
        # alone. ADR 0036, the elision seam.
        original_prefix, original_tail = split_elision(original)
        produced_prefix, produced_tail = split_elision(produced)
        if produced_prefix.casefold() != original_prefix.casefold():
            violations.append(
                Violation(
                    rule="changed_proclitic",
                    offset=offset,
                    found=produced,
                    expected=f"{original_prefix}{original_tail}",
                )
            )
            continue
        index = noun_index(original_tail)
        if produced_tail.casefold() == original_tail.casefold():
            if index is None:
                good += 1
            else:
                # Listed as a noun but left alone: readable as another part of
                # speech here, which no word list can rule out. `ambiguous`
                # counts the position under every reading, so the metric never
                # depends on which one was chosen; `ambiguous_nouns` decides
                # only what the position does to the score.
                ambiguous += 1
                if params.ambiguous_nouns == "free":
                    good += 1
                elif params.ambiguous_nouns == "strict":
                    violations.append(
                        Violation(
                            rule="ambiguous_noun_unchanged",
                            offset=offset,
                            found=produced,
                            expected=f"a displacement of {original_tail!r} (listed as a noun)",
                        )
                    )
                else:
                    undecided += 1
            continue
        if index is None:
            violations.append(
                Violation(
                    rule="changed_a_non_noun",
                    offset=offset,
                    found=produced,
                    expected=original,
                )
            )
            continue
        expected_tail = nouns[(index + params.offset) % len(nouns)]
        # The noun list preserves each language's own capitalisation — German
        # nouns are capitalised, English ones are not — so `expected` must be
        # casefolded too, matching the identity comparison above. Comparing a
        # folded left side to an unfolded right side would silently reject
        # every correct German displacement.
        if produced_tail.casefold() == expected_tail.casefold():
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_displacement",
                    offset=offset,
                    found=produced,
                    expected=f"{original_prefix}{expected_tail}",
                )
            )
    decided = len(candidate) - undecided
    metrics = {"words": float(len(candidate)), "ambiguous_words": float(ambiguous)}
    if decided == 0 and undecided > 0:
        # `_report` scores total == 0 as 1.0 — right for the wordless case the
        # comment below still guards, wrong here: this text has words, every
        # one of them left `undecidable`, and none was ever weighed. Scoring
        # that vacuously satisfied would be the same overconfident verdict
        # `ambiguous_nouns="undecidable"` exists to refuse, one level down.
        # `scheme_violations`' `rhyme_undecidable` (prosody.py) is the same
        # call for the same reason: a partial verdict is honest, an empty one
        # is not.
        return procedure._report(
            good=0,
            total=1,
            violations=[
                Violation(
                    rule="ambiguous_nouns_undecidable",
                    offset=None,
                    found=f"{undecided} word(s) the reading left undecided",
                    expected="at least one position this reading can decide",
                )
            ],
            metrics=metrics,
        )
    return procedure._report(
        good=good,
        # Not max(..., 1): a text and a source that are both wordless agree
        # vacuously, and forcing the total to 1 made that report unsatisfied
        # while listing no violation — a verdict with nothing behind it. The
        # length mismatch above already fails an empty candidate against a
        # source that has words, which is the case the floor was guarding.
        # `undecided` positions are subtracted here rather than counted in
        # `total`: under `ambiguous_nouns="undecidable"` they were never
        # weighed, and counting them would silently discount the score
        # instead of leaving it computed over what was actually judged.
        total=decided,
        violations=violations,
        metrics=metrics,
    )


@register
class NPlus7(ConstructiveProcedure[NPlus7Params, NPlus7ApplyParams]):
    """Lescure's procedure: walk the dictionary seven nouns on."""

    id = "n_plus_7"

    @classmethod
    def params_model(cls) -> type[NPlus7Params]:
        return NPlus7Params

    def _check(self, text: str, pack: LanguagePack, params: NPlus7Params) -> Report:
        return displacement_report(self, text, pack, params)

    @classmethod
    def apply_params_model(cls) -> type[NPlus7ApplyParams]:
        return NPlus7ApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: NPlus7ApplyParams) -> Produced:
        """Walk every noun in `text` seven places down the dictionary."""
        nouns, noun_index = resolve_dictionary(pack, params.dictionary)
        return plain([displace(text, pack, nouns, noun_index, params.offset)])
