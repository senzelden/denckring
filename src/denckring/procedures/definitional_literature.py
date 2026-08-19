"""Definitional literature — each substantive word replaced by its dictionary definition,
and the result put through the same treatment again.

`definitional_expansion` is one round of this; this row is the procedure Bénabou and
Perec actually described, where the expansion is fed back in. It shares that row's
comparison — `unclaimed_run`, imported rather than reimplemented — and adds the one thing
a repeated procedure needs that a single pass does not: a way to ask how deep the text
went.

**Rounds are discovered, not declared.** `check` is given the source and the finished
text and nothing in between, so it tries one round, then two, then three, and reports the
first depth at which every resolvable source word is accounted for in
`metrics["iterations"]`. A writer does not have to say how many times they applied the
procedure, and a text reached in one round is definitional literature as much as one
reached in three — the catalogue definition says *repeat*, not *repeat n times*. An
`iterations` of 0.0 means no round count in range accounts for the text; it is also what
a source with no resolvable word at all reports, since nothing was searched there either,
and `estimated_words` is where that case is disclosed.

**What a round means below the top level.** At depth 1 the question is
`definitional_expansion`'s: does one of the word's glosses appear as a contiguous
unclaimed run? At depth `d` it becomes: is there a gloss of the word whose own
substantive words are each present at depth `d - 1`? So the gloss chosen at each level is
free, exactly as the sense is free at depth 1, and a word inside a gloss that resolves to
nothing — `the`, `of`, `where` — is not required to reappear, the same treatment
unresolvable words get in the source. What this deliberately does not check is that the
nested definitions stay in their original order: at depth 1 word order is checked, since
the gloss must appear as a run, but below that only presence is, because pinning the
nesting positions would mean solving an ambiguous parse of a text where every definition
is stitched to the next without punctuation to separate them. Occurrences are still
counted rather than merely found — the claimed-span bookkeeping of R6 is shared across
every level of one check, so two occurrences of a word need two expansions.

**First fit, and what it costs.** The search takes the first gloss that matches and keeps
it. An adversarial text where an early word's only correct reading is the one a later
word needed can therefore be scored short by a word; no such text has been observed, and
the alternative — backtracking across the whole assignment — multiplies a cost the cap
below already exists to contain.

**The cap is three rounds, and it was measured.** Each round multiplies the search by
every sense of every word of every gloss, and the cost lands on the searches that *fail*,
which cannot stop early. Checked against a genuine three-round expansion of `the cat sat`
(3,679 tokens): depth 3 takes 0.15 s, depth 4 takes 18 s, and depth 5 takes 219 s. Three
rounds is where the checker stays usable and where the procedure's published examples
sit, so a text needing four is reported as reaching none — `metrics["iterations"]` of
0.0 — rather than hanging the caller. `MAX_COMBINATIONS` in `core/prosody.py` is the
codebase's precedent for a cap of this kind, and it is stated in the same place: here.

**Unresolved words are counted, never failed**, and **`apply` is deferred (ADR 0002)**,
both exactly as in `definitional_expansion`; see that module for the reasoning.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.procedures.definitional_expansion import unclaimed_run

#: The deepest expansion `check` will look for. Above this the failing searches stop
#: being interactive; the module docstring carries the measurement behind the number.
MAX_ROUNDS = 3

#: A word's glosses, tokenised and lower-cased once per check rather than once per
#: candidate position — the difference between a fraction of a second and minutes at
#: depth 3.
GlossCache = dict[str, list[list[str]]]


def _tokenised_glosses(word: str, pack: LanguagePack, cache: GlossCache) -> list[list[str]]:
    """Every gloss `pack` records for `word`, as lower-cased token lists, memoised."""
    if word not in cache:
        cache[word] = [
            [token.lower() for token in pack.tokenize(gloss)] for gloss in pack.glosses(word)
        ]
    return cache[word]


def _found_at_depth(
    word: str,
    rounds: int,
    tokens: list[str],
    claimed: list[bool],
    pack: LanguagePack,
    cache: GlossCache,
) -> bool:
    """Whether `word` expanded `rounds` times is present in `tokens`, claiming what it uses.

    At one round a gloss must appear as an unclaimed run. At more, some gloss must have
    all of its own resolvable words present one round shallower. Claims are made on a
    copy until the whole gloss succeeds, so a gloss that matches half way leaves nothing
    behind for the next candidate to trip over.
    """
    for needle in _tokenised_glosses(word, pack, cache):
        if not needle:
            continue
        if rounds == 1:
            span = unclaimed_run(tokens, claimed, needle)
            if span is not None:
                for index in range(*span):
                    claimed[index] = True
                return True
            continue
        trial = list(claimed)
        if all(
            _found_at_depth(inner, rounds - 1, tokens, trial, pack, cache)
            for inner in needle
            if pack.glosses(inner)
        ):
            claimed[:] = trial
            return True
    return False


def _round_result(
    source: str, tokens: list[str], rounds: int, pack: LanguagePack, cache: GlossCache
) -> tuple[list[Violation], int, int, int]:
    """`source` checked against `tokens` at exactly `rounds` rounds.

    Returns `(violations, good, total, unresolved)`, the shape `replaced_by_gloss`
    returns and for the same reasons — `total` and `unresolved` do not depend on the
    round count, only `good` and the violations do.
    """
    claimed = [False] * len(tokens)
    violations: list[Violation] = []
    good = 0
    total = 0
    unresolved = 0
    for offset, word in word_spans(source, pack):
        glosses = pack.glosses(word)
        if not glosses:
            unresolved += 1
            continue
        total += 1
        if _found_at_depth(word, rounds, tokens, claimed, pack, cache):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="not_expanded",
                    offset=offset,
                    found=word,
                    expected=f"one of its {len(glosses)} dictionary definitions, {rounds} "
                    f"round{'s' if rounds > 1 else ''} deep",
                )
            )
    return violations, good, total, unresolved


class DefinitionalLiteratureParams(SourceParams):
    pass


@register
class DefinitionalLiterature(BaseProcedure[DefinitionalLiteratureParams]):
    """Definitional expansion fed back into itself: the source's substantive words
    replaced by their definitions, those definitions' words replaced in turn, for as many
    rounds as the text turns out to have taken."""

    id = "definitional_literature"

    @classmethod
    def params_model(cls) -> type[DefinitionalLiteratureParams]:
        return DefinitionalLiteratureParams

    def _check(self, text: str, pack: LanguagePack, params: DefinitionalLiteratureParams) -> Report:
        tokens = [token.lower() for token in pack.tokenize(text)]
        cache: GlossCache = {}
        closest = _round_result(params.source, tokens, 1, pack, cache)
        found = 0
        if closest[2] == 0:
            # No source word resolves, so no round was searched and none can be claimed;
            # `_report` still scores this 1.0, and `estimated_words` is what discloses it.
            pass
        elif not closest[0]:
            found = 1
        else:
            for rounds in range(2, MAX_ROUNDS + 1):
                result = _round_result(params.source, tokens, rounds, pack, cache)
                if not result[0]:
                    closest, found = result, rounds
                    break
                # Deeper rounds are not always better; keep whichever accounted for most,
                # so the violations reported come from the reading that came closest.
                if result[1] > closest[1]:
                    closest = result
        violations, good, total, unresolved = closest
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"iterations": float(found), "estimated_words": float(unresolved)},
        )
