"""Homosyntaxism — the source's grammar, held word for word, with new content words.

A source-decidable row in the manner of `homoconsonantism`, reading the `pos`
capability of ADR 0045. The comparison is written inline here rather than as a
fifth shape in `denckring.core.source_compare`: that module's docstring records
that its helpers were extracted from real callers instead of designed ahead of
them, and a positional POS correspondence has exactly one caller. A second one
can motivate the extraction.

`apply` is deliberately not shipped. ADR 0002 makes it optional even though the
catalogue marks this row `kind: both`, and `homoconsonantism` is the precedent:
choosing new words of the same class so that they make new sense is invention,
not a mechanical transformation, so a generator here would be writing rather
than transforming. Sampling a lexicon by tag would produce grammatical noise and
call it a procedure.

**What "new words" means here, and why it is not every word.** The catalogue
defines the row as "substituting new words of the same part of speech
throughout", and the obvious reading — every token must differ from the token it
replaces — is not implementable as a rule anyone could satisfy. English closed
classes are tiny and the syntactic frame usually fixes the member: a source
reading *the cat sat on the mat* has two determiners and one preposition, and
demanding a *different* determiner and a *different* preposition at those
positions either forces `a … a … in`, which changes what the sentence says
about definiteness, or has no legal filler at all (there is no second `to` for
an infinitive marker, and none for `of`). Under that reading the procedure would
be near-unsatisfiable on exactly the sentences it is famous for.

So the checker splits the requirement by UD word class. The six open classes —
ADJ, ADV, INTJ, NOUN, PROPN, VERB, which is UD's own list — must carry a *new*
word at every position; the closed classes (ADP, AUX, CCONJ, DET, NUM, PART,
PRON, SCONJ) and the residue (SYM, X) need only keep their tag. That is a
ruling, not a citation: the *Atlas* was not consulted for this module, and the
argument above is the whole of the evidence. It is recorded here and in the
row's catalogue `notes` rather than left implicit, because a definition
promising a substitution the checker does not look for is the defect ADR 0015
names and the one `amphibologia` was cut for.

**What the checker does not verify**, stated plainly so the definition does not
overclaim: it does not check that the result is idiomatic, that it means
anything, or that the substituted words are unrelated to the originals: *The
window kicked the river.* is a satisfied rewriting of *The boy ate the bread.*
A tag sequence is a coarse reading of "the grammatical structure of the
source", and two consequences are measured rather than suspected. Sentence
boundaries do not enter the comparison at all, because the tokens are flattened
after tagging: a two-sentence source is satisfied by a one-sentence text with
the same ten tags in the same order. And two sentences whose phrase boundaries
fall in different places are one structure here. Nothing in this module is a
parse.

The tags come from a model, so the verdict is not exact. The English pack's
tagger is an averaged perceptron trained on UD English-EWT v2.18, measured on
that treebank's held-out test split at 0.9269 joint accuracy and 0.9342 UPOS
accuracy. `PosTag.known` is the per-token half of that honesty: a violation
resting on a form the tagger never saw in training says so in its `note`, and
`metrics["undecided_words"]` counts those positions whether or not they
produced a violation.
"""

from __future__ import annotations

from typing import NamedTuple

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, PosTag, Report, Violation
from denckring.core.registry import register
from denckring.core.text import sentence_spans

#: UD's open word classes, verbatim from the Universal Dependencies POS tag
#: table. These are the positions the row's "new words" clause is checked at;
#: see the module docstring for why the closed classes are exempt.
OPEN_CLASSES = frozenset({"ADJ", "ADV", "INTJ", "NOUN", "PROPN", "VERB"})

_UNKNOWN = "tagged from a form the tagger never saw in training"


class _Token(NamedTuple):
    """One word of a text, at its offset in the whole text, with its reading."""

    offset: int
    word: str
    tag: PosTag


def tagged_tokens(text: str, pack: LanguagePack) -> list[_Token]:
    """Every word of `text`, tagged one sentence at a time.

    Per sentence and not per text: `pos_tags` says a whole text degrades the
    tagging rather than failing it, and leaves the splitting to the caller.
    `core.text.sentence_spans` is that splitter, and is not the line-ending
    punctuation `line_identity` uses, which includes commas — see its docstring
    for the three verdicts that measured the difference.

    Offsets stay whole-text offsets, because a violation must point into the
    text the caller passed and not into whichever sentence it fell in.
    Punctuation is not passed to the tagger, because `word_spans` does not
    return it — and the tagger reads a bare `.` as an unknown NOUN, so
    synthesising one would add a token wrong about itself and about nothing
    else.
    """
    tokens: list[_Token] = []
    for offset, sentence in sentence_spans(text):
        spans = pack.word_spans(sentence)
        for (at, word), tag in zip(spans, pack.pos_tags([w for _, w in spans]), strict=True):
            tokens.append(_Token(offset + at, word, tag))
    return tokens


class HomosyntaxismParams(SourceParams):
    pass


@register
class Homosyntaxism(BaseProcedure[HomosyntaxismParams]):
    """The grammar is the constraint; the content words are the freedom."""

    id = "homosyntaxism"

    @classmethod
    def params_model(cls) -> type[HomosyntaxismParams]:
        return HomosyntaxismParams

    def _check(self, text: str, pack: LanguagePack, params: HomosyntaxismParams) -> Report:
        expected = tagged_tokens(params.source, pack)
        actual = tagged_tokens(text, pack)
        violations: list[Violation] = []
        good = 0
        undecided = 0
        for index, want in enumerate(expected):
            if index >= len(actual):
                # A text shorter than its source has not kept the structure: the
                # missing tail is reported position by position rather than as one
                # summary, because each absent position is a different word class
                # the writer still owes. Offsets are `None` for the reason
                # `rearrangement_report`'s `missing_part` has none — there is no
                # place in the text to point at.
                if not want.tag.known:
                    undecided += 1
                violations.append(
                    Violation(
                        rule="missing_word",
                        offset=None,
                        found="",
                        expected=want.tag.upos,
                        note=_UNKNOWN if not want.tag.known else None,
                    )
                )
                continue
            have = actual[index]
            unknown = not (want.tag.known and have.tag.known)
            undecided += int(unknown)
            note = _UNKNOWN if unknown else None
            if have.tag.upos != want.tag.upos:
                violations.append(
                    Violation(
                        rule="wrong_pos",
                        offset=have.offset,
                        found=have.word,
                        expected=want.tag.upos,
                        note=note,
                    )
                )
            elif want.tag.upos in OPEN_CLASSES and have.word.casefold() == want.word.casefold():
                violations.append(
                    Violation(
                        rule="repeated_word",
                        offset=have.offset,
                        found=have.word,
                        expected=f"a new {want.tag.upos}",
                        note=note,
                    )
                )
            else:
                good += 1
        if len(actual) > len(expected):
            tail = actual[len(expected) :]
            undecided += sum(1 for token in tail if not token.tag.known)
            violations.append(
                Violation(
                    rule="extra_words",
                    offset=tail[0].offset,
                    found=" ".join(token.word for token in tail),
                    expected="",
                    note=_UNKNOWN if any(not token.tag.known for token in tail) else None,
                )
            )
        # `max` and no `, 1` floor, for the reason `letter_class_report` gives:
        # a source with no words at all against a text that has some scores 0
        # with an `extra_words` violation to explain it, so an empty source
        # cannot pass, while an empty text *and* an empty source leave
        # `total == 0`, which `_report` already scores vacuously satisfied.
        total = max(len(expected), len(actual))
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"tokens": float(total), "undecided_words": float(undecided)},
        )
