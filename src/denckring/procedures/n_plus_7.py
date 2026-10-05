"""N+7 — every noun replaced by the seventh noun after it in the dictionary."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import Field, field_validator

from denckring.core.base import (
    ApplyParams,
    BaseProcedure,
    ConstructiveProcedure,
    IdentityParams,
    SourceParams,
    plain,
)
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import align, gaps, unchanged
from denckring.core.text import split_elision, word_spans

#: The three readings of an unchanged listed word (`NPlus7Params.ambiguous_nouns`).
AmbiguousNouns = Literal["undecidable", "free", "strict"]


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


class NPlus7Params(SourceParams, IdentityParams):
    offset: int = Field(
        default=7, description="How many nouns to count forward.", json_schema_extra=param("task")
    )
    dictionary: list[str] | None = Field(
        default=None,
        description=(
            "The ordered word list to displace within. Defaults to the pack's "
            "nouns, which a reader is not shown: `denckring.nouns(lang)` lists "
            "them, and `nouns(lang, max_band=...)` the everyday ones, for a prompt "
            "to print. Order is the contract: N+7 walks the seventh entry after a "
            "word, so a supplied list's order is the caller's editorial choice."
        ),
        json_schema_extra=param("material", "word"),
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
    #
    # `None` resolves in the checker (`ambiguous_reading`), the house convention
    # for a value read off the call. A supplied list is the caller saying which
    # words are nouns here, so a listed word left alone is a missed displacement
    # (`strict`); the pack's list cannot say that, so it keeps `free`. ADR 0055.
    ambiguous_nouns: AmbiguousNouns | None = Field(
        default=None,
        description=(
            "What an unchanged word that the dictionary lists means: leave the "
            "position unscored (undecidable), accept it (free), or fail it "
            "(strict). Unset: strict with a supplied dictionary, free with the "
            "pack's nouns."
        ),
        json_schema_extra=param("policy"),
    )
    # Opt-in, so 0.3.2 moves no verdict. Under `free` or `undecidable` a text in
    # which every listed word was left alone passes, each one plausibly another
    # part of speech; taken together that is not an N+7 however each word reads.
    # The rule name is `paronomasia`'s, for the same failure.
    require_displacement: bool = Field(
        default=False,
        description=(
            "Fail a text in which no word the dictionary lists was displaced, as "
            "`no_displacement`, whatever `ambiguous_nouns` makes of each one."
        ),
        json_schema_extra=param("switch"),
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


def ambiguous_reading(params: NPlus7Params) -> AmbiguousNouns:
    """The reading `ambiguous_nouns` names, with `None` resolved (ADR 0055):
    `strict` when the caller supplied `dictionary`, `free` with the pack's."""
    if params.ambiguous_nouns is not None:
        return params.ambiguous_nouns
    return "strict" if params.dictionary is not None else "free"


def _moves(
    word: str,
    nouns: Sequence[str],
    noun_index: Callable[[str], int | None],
    offset: int,
) -> bool:
    """Whether displacing `word` changes it: it is listed, and the walk does not
    come back round to it (an offset that is a multiple of the list's length)."""
    _, tail = split_elision(word)
    index = noun_index(tail)
    return index is not None and nouns[(index + offset) % len(nouns)].casefold() != tail.casefold()


class NPlus7ApplyParams(ApplyParams, NPlus7Params):
    pass


Pair = tuple[tuple[int, str], tuple[int, str]]


def _pairing(
    candidate: list[tuple[int, str]],
    source: list[tuple[int, str]],
    nouns: Sequence[str],
    noun_index: Callable[[str], int | None],
    offset: int,
    *,
    end: int,
) -> tuple[list[Pair | None], dict[int, Violation]]:
    """Which candidate word answers which source word, one entry per unit.

    With as many words as the source, word for word, as it always was. With a
    different count, the old report scored the whole text 0/1 as
    `wrong_word_count`, so one dropped article cost every displacement after it
    (audit A6). The two are aligned instead (ADR 0056), against the text a
    correct N+7 would be: each listed word displaced, every other word as it
    stands. The pairs are then judged as before, and each word inserted or
    missing is an entry of its own, `None`, with its violation in the dict
    (`source_compare.gaps`). A listed word left alone aligns as a substitution,
    which pairs it with its source word all the same, so the reading in
    `ambiguous_nouns` still decides it. The equal-count path is left word for
    word on purpose: an alignment could pair a word with a later word of the
    same spelling, and only a dropped or added word is what A6 is about.
    """
    if len(candidate) == len(source):
        return list(zip(candidate, source, strict=True)), {}

    def correct(word: str) -> str:
        prefix, tail = split_elision(word)
        index = noun_index(tail)
        if index is None:
            return word
        return f"{prefix}{nouns[(index + offset) % len(nouns)]}"

    expected = [correct(word) for _, word in source]
    steps = align(
        [word.casefold() for word in expected], [word.casefold() for _, word in candidate]
    )
    unpaired = gaps(
        steps,
        expected,
        candidate,
        inserted="extra_words",
        deleted="missing_word",
        joiner=" ",
        end=end,
    )
    pairs: list[Pair | None] = [
        (candidate[j], source[i]) if i is not None and j is not None else None for _, i, j in steps
    ]
    return pairs, unpaired


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
    accepted (`free`, the default with the pack's nouns, and what shipped before
    this parameter existed), left out of the score entirely (`undecidable`), or
    failed (`strict`, the default with a supplied dictionary since ADR 0055).
    Every reading reports the same `ambiguous_words` count, in the
    same way `estimated_words` keeps the syllable heuristic honest — only what
    the count does to the score changes.
    """
    candidate = word_spans(text, pack)
    source = word_spans(params.source, pack)
    nouns, noun_index = resolve_dictionary(pack, params.dictionary)
    reading = ambiguous_reading(params)
    violations: list[Violation] = []

    steps, unpaired = _pairing(candidate, source, nouns, noun_index, params.offset, end=len(text))
    ambiguous = 0
    undecided = 0
    displaced = 0
    good = 0
    for position, pair in enumerate(steps):
        if pair is None:
            # A run of inserted words is one violation, keyed at its first step.
            if position in unpaired:
                violations.append(unpaired[position])
            continue
        (offset, produced), (_, original) = pair
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
            # A listed word whose walk comes back round to it (an offset that
            # is a multiple of the list's length) is displaced correctly by
            # being left alone, so no reading has anything to judge. Under
            # `strict`, now the default with a supplied list (ADR 0055), it
            # was failed, which left a copy of such a source, its only answer,
            # unsatisfiable (ruling R-U2a).
            if index is None or not _moves(original, nouns, noun_index, params.offset):
                good += 1
            else:
                # Listed as a noun but left alone: readable as another part of
                # speech here, which no word list can rule out. `ambiguous`
                # counts the position under every reading, so the metric never
                # depends on which one was chosen; `ambiguous_nouns` decides
                # only what the position does to the score.
                ambiguous += 1
                if reading == "free":
                    good += 1
                elif reading == "strict":
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
        displaced += 1
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
    # Every step of the alignment is a unit: each word inserted or missing
    # counts once, beside the pairs judged above.
    decided = len(steps) - undecided
    metrics = {"words": float(len(candidate)), "ambiguous_words": float(ambiguous)}
    # Each refusal is one more unit, failed, on top of whatever was weighed.
    refused = unchanged(
        text,
        params.source,
        pack,
        allow=params.allow_identity,
        alternative=lambda: any(
            _moves(original, nouns, noun_index, params.offset) for _, original in source
        ),
        fold=False,
    )
    if params.require_displacement and displaced == 0:
        refused.append(
            Violation(
                rule="no_displacement",
                offset=None,
                found="no listed word displaced",
                expected=f"at least one listed word moved {params.offset} places on",
            )
        )
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
            total=1 + len(refused),
            violations=[
                Violation(
                    rule="ambiguous_nouns_undecidable",
                    offset=None,
                    found=f"{undecided} word(s) the reading left undecided",
                    expected="at least one position this reading can decide",
                ),
                *refused,
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
        total=decided + len(refused),
        violations=violations + refused,
        metrics=metrics,
    )


@register
class NPlus7(ConstructiveProcedure[NPlus7Params, NPlus7ApplyParams]):
    """Lescure's procedure: walk the dictionary seven nouns on."""

    id = "n_plus_7"
    rules = (
        "ambiguous_noun_unchanged",
        "ambiguous_nouns_undecidable",
        "changed_a_non_noun",
        "changed_proclitic",
        "extra_words",
        "missing_word",
        "no_displacement",
        "unchanged",
        "wrong_displacement",
    )

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
