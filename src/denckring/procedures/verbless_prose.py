"""Verbless prose — a text carrying its sense without a single finite verb.

The verdict rests on a statistical part-of-speech tagger, so it is an estimate and
not a fact about the text. `syllable_count` says the same thing about spellings it
cannot look up; here there is no tier that looks anything up at all. ADR 0045
records the measurement: on UD English-EWT v2.18's held-out test split the tagger
scores joint accuracy 0.9269, UPOS accuracy 0.9342, and for finite verbs
precision 0.9482, recall 0.9498, F1 0.9490 over 21,885 tokens. Read plainly, that
is roughly one finite verb in twenty slipping through unflagged and roughly one
flagged token in twenty that was never a finite verb. A `satisfied` report from
this row is therefore evidence, not proof, and the two metrics it carries —
`words` and `undecided_words` — are what let a reader weigh it.

`apply` is deliberately not shipped. The catalogue marks the row `kind:
restrictive` and ADR 0002 makes `apply` optional; rewriting a passage so its
finite verbs become participles and apposition is composition rather than a
mechanical transformation, so there is nothing here for a generator to do that
would not just be writing. `homoconsonantism` documents the same choice.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import _SENTENCE_END, word_spans


def sentence_groups(text: str, pack: LanguagePack) -> list[list[tuple[int, str]]]:
    """The text's words as `(offset, word)`, grouped into sentences.

    `pack.pos_tags` wants one sentence at a time — *walks* is a noun in *the
    evening walks* and a finite verb in *she walks*, and the context is the whole
    of what makes the answer worth having — while a `Violation` must point into
    the text the caller passed. So the grouping is done over `word_spans`, whose
    offsets are already the whole text's, rather than by slicing the text into
    sentences and tagging the slices with offsets of their own.

    A group ends wherever `_SENTENCE_END` appears in the gap between two words —
    sentence-final punctuation only, never a comma.

    Which constant this is matters more than it looks, and the first version of
    this function used the wrong one. `_TERMINAL_PUNCTUATION`'s comment calls it
    "sentence punctuation", but it carries `,;:` — it is the set a *line* may end
    on, used for stripping a refrain's tail. Splitting on it hands the tagger
    clause fragments, and the tagger is trained on whole sentences.

    Measured over ten comma-heavy texts: three get a different verdict, and
    clause-splitting is wrong in **all three**. It reports a finite verb in *The
    lamps, unlit, above the empty road* and in *She walks home, tired*, neither of
    which has one. That is not an incidental loss — apposition set off by commas
    is the characteristic shape of verbless prose, so the splitting that breaks it
    breaks precisely this row's subject matter.
    """
    groups: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    previous_end = 0
    for offset, word in word_spans(text, pack):
        if current and any(ch in _SENTENCE_END for ch in text[previous_end:offset]):
            groups.append(current)
            current = []
        current.append((offset, word))
        previous_end = offset + len(word)
    if current:
        groups.append(current)
    return groups


class VerblessProseParams(BaseModel):
    pass


@register
class VerblessProse(BaseProcedure[VerblessProseParams]):
    """Nouns, participles and apposition carry it; no finite verb may."""

    id = "verbless_prose"

    @classmethod
    def params_model(cls) -> type[VerblessProseParams]:
        return VerblessProseParams

    def _check(self, text: str, pack: LanguagePack, params: VerblessProseParams) -> Report:
        violations: list[Violation] = []
        words = 0
        undecided = 0
        for group in sentence_groups(text, pack):
            tags = pack.pos_tags([word for _, word in group])
            for (offset, word), tag in zip(group, tags, strict=True):
                words += 1
                if not tag.known:
                    undecided += 1
                if tag.verb_form == "Fin":
                    violations.append(
                        Violation(
                            rule="finite_verb",
                            offset=offset,
                            found=word,
                            expected="a participle, a noun or an apposition instead",
                            # The tagger answers for every token, including one
                            # whose form it never saw, by falling back on suffix
                            # and shape. A violation resting on that has to say so
                            # (ADR 0045); `undecided_words` counts them, this names
                            # the one the reader is being asked to change.
                            note=(
                                None
                                if tag.known
                                else "tagged from a form the tagger never saw in training"
                            ),
                        )
                    )
        return self._report(
            good=words - len(violations),
            total=words,
            violations=violations,
            metrics={"words": float(words), "undecided_words": float(undecided)},
        )
