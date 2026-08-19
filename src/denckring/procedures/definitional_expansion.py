"""Definitional expansion — each substantive word replaced once by its dictionary
definition.

One iteration of Bénabou and Perec's *littérature définitionnelle*; `definitional_literature`
(a later task) is the row that repeats this to a fixed point rather than stopping at one pass.

**Comparison rule, decided by running it against real OEWN text, not by reasoning about
it.** `get_pack("en").glosses("cat")` returns ten senses carrying parentheses (`(baseball)
an advance...`), semicolons (`domestic cats; wildcats`), colons and apostrophes —
punctuation a writer retyping a definition by hand will not reproduce character for
character, and punctuation that has nothing to do with whether the word was expanded. A
literal-substring match would gate satisfiability on that punctuation surviving
untouched, which is the same shape of mistake that made `synonymic_substitution`
unsatisfiable for a different reason (see its catalogue `notes`). So a gloss counts as
present if its own word *tokens* — lower-cased, taken with the same `pack.tokenize` the
rest of the row uses, which already drops every non-letter character — appear as a
contiguous run inside the candidate text's tokens, in the gloss's own word order. That is
stricter than "the gloss's words appear somewhere, in any order" (which would accept a
scrambled definition as though it had been quoted) and looser than "the exact string
appears" (which would reject a gloss that survived a straight/curly quote substitution, a
re-cased sentence-initial word, or a comma standing in for the source's semicolon).
Measured against the corpus, punctuation and case carry no signal this constraint needs,
so both are folded away; word choice and word order are what is checked.

**Any one sense counts.** `pack.glosses` returns every sense OEWN records for a word, and
resolution is best-effort, not a guarantee: `pack.glosses("sat")` returns only the
Saturday-abbreviation sense, nothing to do with sitting — the same shape of collision the
capability's own contract cites for `glosses("aides")` returning the Hades sense.
Requiring the "right" sense would need a discrimination the pack does not offer, and
would fail a correct expansion for a reason outside the writer's control. So this row
accepts any of a word's glosses, not one it has picked out in advance.

**Unresolved words are counted, never failed.** A source word `pack.glosses` cannot
resolve — an irregular form such as `went`, or a function word such as `the`, both of
which come back as `()` — is tallied into `metrics["estimated_words"]` and affects
neither `good` nor `total`, the same contract the syllable, stress and rhyme paths
already share.

**`apply` is deferred (ADR 0002).** `check` is what registration requires; a generator
that reliably picks one sense per substantive word and produces text this checker's own
tokenisation accepts is future work, not this task's — the catalogue's `kind: both`
records what the form permits, not what this row ships.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


def _gloss_present(candidate_tokens: list[str], gloss: str, pack: LanguagePack) -> bool:
    """Whether `gloss`'s own word tokens appear, in order, as a run in `candidate_tokens`.

    Both sides are lower-cased and tokenised with `pack.tokenize`, so parentheses,
    semicolons, colons and quotation marks in the gloss — and any case difference from
    the candidate text re-casing a sentence-initial word — never gate the match. See the
    module docstring for why this is the comparison this row uses.
    """
    needle = [token.lower() for token in pack.tokenize(gloss)]
    if not needle:
        return False
    span = len(needle)
    return any(
        candidate_tokens[start : start + span] == needle
        for start in range(len(candidate_tokens) - span + 1)
    )


def _replaced_by_gloss(
    source: str, text: str, pack: LanguagePack
) -> tuple[list[Violation], int, int, int]:
    """Check every substantive word of `source` against `text`.

    Walks `source`'s words in order. A word `pack.glosses` cannot resolve is counted as
    unresolved and never scored. A word that resolves is scored `good` if any one of its
    glosses is present in `text` (see `_gloss_present`), and reported as `not_expanded`
    otherwise. Returns `(violations, good, total, unresolved)` — `definitional_literature`
    consumes this by name.
    """
    candidate_tokens = [token.lower() for token in pack.tokenize(text)]
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
        if any(_gloss_present(candidate_tokens, gloss, pack) for gloss in glosses):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="not_expanded",
                    offset=offset,
                    found=word,
                    expected=f"one of its {len(glosses)} dictionary definitions",
                )
            )
    return violations, good, total, unresolved


class DefinitionalExpansionParams(SourceParams):
    pass


@register
class DefinitionalExpansion(BaseProcedure[DefinitionalExpansionParams]):
    """A single pass of definitional literature: every resolvable substantive word of the
    source replaced once by one of its dictionary definitions."""

    id = "definitional_expansion"

    @classmethod
    def params_model(cls) -> type[DefinitionalExpansionParams]:
        return DefinitionalExpansionParams

    def _check(self, text: str, pack: LanguagePack, params: DefinitionalExpansionParams) -> Report:
        violations, good, total, unresolved = _replaced_by_gloss(params.source, text, pack)
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"estimated_words": float(unresolved)},
        )
