"""Chimera — one text's frame, refilled from three others.

A `checkability: source` row reading the `pos` capability of ADR 0045, in the
manner of `homosyntaxism`: the frame and the candidate are tagged one sentence
at a time and compared position by position. What differs is what each position
owes. Where the frame carries a NOUN, a VERB or an ADJ, the candidate owes a
word of that class *drawn from the matching donor*; everywhere else it owes the
frame's own word, because the frame is what survives the operation.

**The parameter shape, and why `core/base.py` is untouched.** Issue #22 and ADR
0045 both record this row as blocked on a parameter-shape decision, on the
grounds that "`SourceParams` carries one source and chimera needs three". That
framing is wrong, and naming why is the whole of the decision. `SourceParams`
means *the text this one was made from* — and this text was made from the
frame. The frame is the source, already covered, and `apply` already supplies it
from its own text argument (`parse_apply_params`). The three donors are not
sources in that sense at all: they are lexical stock, three word lists that
happen to be written as texts. So they are three ordinary fields beside the
inherited one, and no mixin, no `SourcesParams`, and no change to
`core/base.py` is needed.

Two alternatives were considered and rejected:

- **An ordered `sources: list[str]`.** Position would silently encode which
  donor fills which word class, and `params_schema()` — the surface every
  non-Python caller reads — cannot say that. A caller would have to know from
  prose that element 1 is the verbs. Role-keyed names say it in the schema.
- **A `SourcesParams` mixin in `core/base.py`.** It would generalise a shape
  with exactly one caller, and generalise the wrong thing: a list of *sources*
  is not what this row has, per the paragraph above. `source_compare`'s
  docstring records the house rule — extract from real callers rather than
  ahead of them.

**Four rulings this module makes, none of them citations.**

1. **A donor with no word of the class it owes.** `apply` refuses, with
   `InvalidParams` naming the empty class and the field it came from — but only
   when the frame actually has a position of that class to fill, because a frame
   with no adjective in it is not harmed by an adjectiveless `adjectives_from`.
   `check` never refuses: an empty donor makes the constraint unsatisfiable, not
   malformed, and a checker's job is to return a verdict. Every target position
   then fails `not_from_donor` and the score says so. This is the split
   `cent_mille_milliards` already draws — its `_check` reports `missing_line`
   for a position its `_produce` refuses to run on.

2. **Repetition.** A drawn word may repeat within the output, and the checker
   does not look for repetition at all. Donors are short texts; requiring
   distinctness would make the row fail on any frame with more nouns than its
   donor has, which is most of them. A drawn word may also equal the word it
   replaced — the definition asks where a word *came from*, not that it be new,
   which is the opposite of `homosyntaxism`'s "new words" clause and deliberately
   so: there the source is the thing being rewritten, here the donor is a lexicon
   and a coincidence of vocabulary is not a failure to run the procedure.
   `_produce` still prefers a word other than the one it replaces where the donor
   offers one, so the generator does not manufacture its own degenerate output.

   This makes a third check/apply asymmetry, beside the two ruling 1 draws, and
   it is a consequence of this ruling rather than an oversight: where every pool
   collapses to the frame's own word — frame *The cold wind blows.* with pools
   `{wind}`, `{blows}`, `{cold}` — `_produce` has nothing else to draw, returns
   the frame unchanged, and the **spine** raises `DegenerateOutput`, while
   `check` reports the frame satisfied by itself. Both are right. The text does
   satisfy the constraint, and a generator handing back its own input is what
   `allow_identity` exists to make the caller ask for.

3. **Case.** A substituted word inherits the frame word's capitalisation:
   ALL CAPS from ALL CAPS, Initial from Initial, and lower-cased where the frame
   word was lower-case. Capitalisation here is a fact about the position — a
   sentence opening, a shout — and the position is part of the frame, which
   survives. Punctuation and spacing survive for the same reason and by the same
   means as `n_plus_7.displace`: word spans are substituted in place rather than
   re-joined.

4. **The frame's other words** are compared casefolded, not exactly. Every
   source-comparing row here already does (`homosyntaxism`'s `repeated_word`,
   `n_plus_7`'s `displacement_report`), and a candidate differing from the frame
   only in the capitalisation of a determiner has not refilled anything; failing
   it would report a typographic difference under a rule about word classes.
   Donor membership is tested casefolded for the same reason, which is also what
   makes ruling 3 safe: inherited capitalisation can never itself be a violation.

**What the checker does not verify**, so the definition does not overclaim: that
the result reads as English, that the donors were used *evenly*, or that a word
found in the donor was taken from it rather than arrived at independently —
membership is all a text can witness. And the tags come from a model, so the
verdict is an estimate. `PosTag.known` carries that through: a violation resting
on a form the tagger never saw in training says so in its `note`, and
`metrics["undecided_words"]` counts those positions whether or not they produced
a violation. ADR 0045 records the tagger's measured accuracy.

**And `apply` searches greedily, so a refusal is this search's failure and not a
proof that no filling exists.** `_produce` fixes one position at a time and never
revisits a position it has already settled, so `NoCandidateWord` means *this*
search ran out of words at one position, not that the frame and these donors are
unsatisfiable — a counterexample is measured in `docs/audit/chimera.md`. A
complete search over three pools is exponential and this row does not need one;
what it needs is a message that does not claim more than it knows. The
`forced_positions` metric on each candidate reports the other end of the same
honesty: how many positions of *this* output had exactly one donor word that
survives tagging there, and so could not have gone otherwise. Where the whole
output is forced, `seed` is a documented parameter that changes nothing.
"""

from __future__ import annotations

import random

from pydantic import Field

from denckring.core.base import (
    ApplyParams,
    ConstructiveProcedure,
    SeedParams,
    SourceParams,
)
from denckring.core.errors import InvalidParams, NoCandidateWord
from denckring.core.protocol import Candidate, LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import sentence_spans
from denckring.procedures.homosyntaxism import tagged_tokens

#: The three word classes this row strips out and refills, mapped to the
#: parameter each is refilled from. UD tags, as `PosTag.upos` carries them.
#: PROPN is deliberately not a target: a name is not a noun the procedure may
#: swap for another name without changing who the text is about.
DONOR_OF = {"NOUN": "nouns_from", "VERB": "verbs_from", "ADJ": "adjectives_from"}

_UNKNOWN = "tagged from a form the tagger never saw in training"


def donor_words(text: str, pack: LanguagePack, upos: str) -> list[str]:
    """The donor's words of one class, in order of first appearance, deduped.

    Order is first-appearance and the dedupe is casefolded, so the pool a draw
    runs over is a function of the donor text alone — two calls with the same
    seed and the same donor draw the same word. A pool built from a set would
    make the draw depend on hash ordering, which is exactly the reproducibility
    `SeedParams` exists to promise.
    """
    pool: list[str] = []
    seen: set[str] = set()
    for token in tagged_tokens(text, pack):
        if token.tag.upos == upos and token.word.casefold() not in seen:
            seen.add(token.word.casefold())
            pool.append(token.word)
    return pool


def recase(word: str, model: str) -> str:
    """`word`, capitalised the way the frame word it replaces was.

    Ruling 3 in the module docstring. `isupper()` is guarded by a length test
    because a one-letter lower-case word has no upper form to distinguish, and
    a single capital is Initial rather than ALL CAPS.
    """
    if len(model) > 1 and model.isupper():
        return word.upper()
    if model[:1].isupper():
        return word[:1].upper() + word[1:]
    return word.lower()


def _refill(text: str, targets: list[tuple[int, str]], drawn: dict[int, str]) -> str:
    """`text` with each target position replaced by the word drawn for it.

    A target is an `(offset, word)` span rather than a tagged token, so this
    says in its signature that it does not consult a tag: everything the
    rebuilding needs is where the old word was and how it was written.

    Word spans are substituted in place and everything between them is copied,
    so punctuation, spacing and line breaks survive — `n_plus_7.displace`'s
    approach, for its reason: a generator that normalised the whitespace would
    produce text its own checker then rejected for the wrong reason.
    """
    pieces: list[str] = []
    cursor = 0
    for offset, word in targets:
        pieces.append(text[cursor:offset])
        pieces.append(recase(drawn[offset], word))
        cursor = offset + len(word)
    pieces.append(text[cursor:])
    return "".join(pieces)


def _forced_positions(
    candidate: str,
    pack: LanguagePack,
    slots: list[tuple[int, int, str, str]],
    pools: dict[str, list[str]],
) -> int:
    """How many of the filled positions had exactly one word that survives there.

    A pool of six nouns is not six choices. A word's class is a fact about its
    position, so most of a pool can fail to read as its own class in a given
    slot, and nothing a caller reads — the definition, `params_schema()`, the
    output itself — says which positions were free and which were forced.
    Measured: pools of four NOUN, two VERB and one ADJ over *The quick boy
    opened the door.* give fourteen distinct outputs across twenty seeds and the
    adjective is `bright` in every one of them. `seed` is a documented parameter
    doing nothing at that position, and this is the count that says so — the
    `undecided_words` / `PosTag.known` / `Production.truncated` idiom: report the
    limit rather than let the shape of the surface imply it away.

    A `slot` is `(offset in the candidate, length of the word standing there,
    the class owed, the frame word it replaced)`. Each trial varies one position
    of the accepted candidate and leaves the rest, so every count is at least
    one — the drawn word itself survives — and the answer is about the text the
    caller is actually given. It is therefore a statement about *this* output
    and not about the parameters: another seed can leave a different set of
    positions forced, because what survives at a position depends on what the
    positions around it hold. A count answered from the pool sizes alone would
    be cheaper and would miss exactly the collapse above.

    **Only the sentence the position falls in is re-tagged**, not the whole
    text, and that is the difference between a metric and a tax: `tagged_tokens`
    already tags sentence by sentence, so a substitution cannot change any other
    sentence's reading. Measured on a 680-word frame with pools of 13/6/8 over
    480 filled positions: whole-text re-tagging cost 21.1 s, sentence-local
    re-tagging 0.34 s, and both returned the same count.
    """
    sentences = sentence_spans(candidate)
    forced = 0
    for offset, length, upos, model in slots:
        start, sentence = max((s for s in sentences if s[0] <= offset), key=lambda s: s[0])
        local = offset - start
        spans = pack.word_spans(sentence)
        index = next(position for position, (at, _) in enumerate(spans) if at == local)
        survivors = 0
        for word in pools[upos]:
            trial = sentence[:local] + recase(word, model) + sentence[local + length :]
            trial_spans = pack.word_spans(trial)
            # A trial word that retokenised into two does not answer this
            # position at all, so it is not a survivor rather than an error —
            # the same guard `_produce` raises on, met here where there is a
            # cheaper answer than refusing.
            if len(trial_spans) != len(spans):
                continue  # pragma: no cover - defensive; one token per pool word
            if pack.pos_tags([w for _, w in trial_spans])[index].upos == upos:
                survivors += 1
        forced += int(survivors == 1)
    return forced


class ChimeraParams(SourceParams):
    """`source` is the frame; the three donors are lexical stock, not sources.

    See the module docstring for why that distinction is the row's whole
    parameter-shape decision, and why it needs nothing from `core/base.py`.
    `apply` supplies `source` from its own text argument and refuses a caller
    who passes a second one.
    """

    nouns_from: str = Field(description="The text the nouns are taken from.")
    verbs_from: str = Field(description="The text the verbs are taken from.")
    adjectives_from: str = Field(description="The text the adjectives are taken from.")


class ChimeraApplyParams(ChimeraParams, SeedParams, ApplyParams):
    pass


@register
class Chimera(ConstructiveProcedure[ChimeraParams, ChimeraApplyParams]):
    """One text's grammar and function words, three others' content words."""

    id = "chimera"

    @classmethod
    def params_model(cls) -> type[ChimeraParams]:
        return ChimeraParams

    def _pools(self, params: ChimeraParams, pack: LanguagePack) -> dict[str, list[str]]:
        """Each target class's donor pool, keyed by UD tag."""
        return {
            upos: donor_words(getattr(params, field), pack, upos)
            for upos, field in DONOR_OF.items()
        }

    def _check(self, text: str, pack: LanguagePack, params: ChimeraParams) -> Report:
        frame = tagged_tokens(params.source, pack)
        actual = tagged_tokens(text, pack)
        pools = {
            upos: {word.casefold() for word in words}
            for upos, words in self._pools(params, pack).items()
        }
        violations: list[Violation] = []
        good = 0
        undecided = 0
        for index, want in enumerate(frame):
            if index >= len(actual):
                # Position by position rather than one summary, for the reason
                # `homosyntaxism`'s `missing_word` gives: each absent position is
                # a different thing the writer still owes. No offset, because
                # there is no place in the text to point at.
                if not want.tag.known:
                    undecided += 1
                violations.append(
                    Violation(
                        rule="missing_word",
                        offset=None,
                        found="",
                        expected=(
                            f"{want.tag.upos} from {DONOR_OF[want.tag.upos]}"
                            if want.tag.upos in DONOR_OF
                            else want.word
                        ),
                        note=_UNKNOWN if not want.tag.known else None,
                    )
                )
                continue
            have = actual[index]
            unknown = not (want.tag.known and have.tag.known)
            undecided += int(unknown)
            note = _UNKNOWN if unknown else None
            if want.tag.upos not in DONOR_OF:
                # The frame is what survives: anything that is not a noun, a verb
                # or an adjective must still be the frame's own word. Ruling 4 —
                # casefolded, so a capitalised determiner is not a violation.
                if have.word.casefold() == want.word.casefold():
                    good += 1
                else:
                    violations.append(
                        Violation(
                            rule="frame_word_changed",
                            offset=have.offset,
                            found=have.word,
                            expected=want.word,
                            note=note,
                        )
                    )
            elif have.tag.upos != want.tag.upos:
                violations.append(
                    Violation(
                        rule="wrong_pos",
                        offset=have.offset,
                        found=have.word,
                        expected=want.tag.upos,
                        note=note,
                    )
                )
            elif have.word.casefold() not in pools[want.tag.upos]:
                violations.append(
                    Violation(
                        rule="not_from_donor",
                        offset=have.offset,
                        found=have.word,
                        expected=f"{want.tag.upos} from {DONOR_OF[want.tag.upos]}",
                        note=note,
                    )
                )
            else:
                good += 1
        if len(actual) > len(frame):
            tail = actual[len(frame) :]
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
        # `max` and no `, 1` floor, exactly as `homosyntaxism` argues it: an
        # empty frame against a text with words scores 0 with `extra_words` to
        # explain it, while both empty leaves `total == 0`, which `_report`
        # already scores vacuously satisfied.
        total = max(len(frame), len(actual))
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"tokens": float(total), "undecided_words": float(undecided)},
        )

    @classmethod
    def apply_params_model(cls) -> type[ChimeraApplyParams]:
        return ChimeraApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: ChimeraApplyParams) -> Produced:
        """Empty the text of its nouns, verbs and adjectives; refill each from its donor.

        The rebuilding follows `n_plus_7.displace`: substitute each word span in
        place and keep everything between the spans, so punctuation and spacing
        survive and the checker compares position against position rather than
        re-tokenising a normalised text. `displace` itself cannot be reused —
        it walks an ordered noun list by index over `word_spans`, where this
        walks tagged tokens and draws from a pool — so the approach is shared
        and the code is not.

        **The draw is verified against the tagger, and that is not belt and
        braces.** A word's class is a fact about its position, not about the
        word: drawing the noun `salt` into a sentence-initial noun slot gives
        `Salt watched the water.`, where the tagger reads `Salt` as PROPN — so
        the generator had produced text its own checker rejects, measured on
        the very first ordinary text it was audited against (docs/audit/
        chimera.md). Choosing blind and hoping is how `slenderizing` shipped.
        So each pass re-tags its own output and redraws only the positions
        whose class did not survive, from the words not yet tried there.

        **That search is greedy coordinate descent, and it is incomplete.** A
        position that is redrawn keeps every other position's word, and a word
        once tried at a position is never tried there again — so when the words
        left at a position run out, what has been shown is that *this* walk
        failed, not that the position cannot be filled. Because a word's class
        depends on its context, a different draw elsewhere can make a word that
        failed here work. `docs/audit/chimera.md` records a measured case: a
        frame these donors do satisfy, which `apply` refuses at seed 0. The
        refusal says so. No artificial budget bounds the loop and none is needed
        — every pass that does not return marks at least one more word tried at
        some position, the pools are finite, so the loop terminates — but
        terminating is all the bound buys, and completeness is not on offer:
        searching every combination over three pools is exponential and no row
        here needs that.

        Each candidate carries `target_positions` and `forced_positions`. The
        second counts the positions of the returned text where exactly one pool
        word survives tagging, given what the other positions hold — the fact a
        caller cannot otherwise see, since the donors look like more choice than
        they are. Where it equals the first, `seed` changed nothing.
        """
        chooser = random.Random(params.seed)
        pools = self._pools(params, pack)
        frame = tagged_tokens(text, pack)
        targets = [token for token in frame if token.tag.upos in DONOR_OF]
        for token in targets:
            if not pools[token.tag.upos]:
                # Ruling 1: refused here, and only here, and only once the frame
                # is known to have a position of this class. A caller who asked
                # for verbs from a text with no verb in it gets told which of
                # their three donors was empty, rather than a text that silently
                # kept the frame's own verbs and then fails its own checker.
                raise InvalidParams(
                    self.id,
                    f"{DONOR_OF[token.tag.upos]} supplies no {token.tag.upos} to refill "
                    f"{token.word!r} with",
                )
        tried: dict[int, set[str]] = {token.offset: set() for token in targets}
        drawn: dict[int, str] = {}
        redraw = list(targets)
        while True:
            for token in redraw:
                pool = [word for word in pools[token.tag.upos] if word not in tried[token.offset]]
                if not pool:
                    # Not "no word can stand here": this search is greedy and
                    # never revisits the positions it has already settled, so
                    # another filling may exist that it cannot reach. Measured
                    # in docs/audit/chimera.md.
                    raise NoCandidateWord(
                        self.id,
                        f"this greedy search found no {token.tag.upos} in "
                        f"{DONOR_OF[token.tag.upos]} that still reads as {token.tag.upos} where "
                        f"{token.word!r} stands; it does not revisit the other positions, so a "
                        f"filling it cannot reach may still exist",
                    )
                # Ruling 2: repetition is allowed, but a draw that reproduces the
                # word it replaces is avoided while the pool offers anything else.
                others = [word for word in pool if word.casefold() != token.word.casefold()]
                word = chooser.choice(others or pool)
                tried[token.offset].add(word)
                drawn[token.offset] = word
            candidate = _refill(text, [(t.offset, t.word) for t in targets], drawn)
            retagged = tagged_tokens(candidate, pack)
            # A substitution that changes how many words the text has would make
            # every position after it answer the wrong frame position, and
            # nothing downstream could tell. Not reachable through a pool built
            # by `donor_words`, whose entries are single tokens by construction
            # — so this is a guard, not a handled case.
            if len(retagged) != len(frame):
                raise NoCandidateWord(  # pragma: no cover - defensive; one token per pool word
                    self.id, "a drawn word did not come back from the tokeniser as one word"
                )
            redraw = [
                token
                for token, refilled in zip(frame, retagged, strict=True)
                if token.tag.upos in DONOR_OF and refilled.tag.upos != token.tag.upos
            ]
            if not redraw:
                slots = [
                    (filled.offset, len(filled.word), token.tag.upos, token.word)
                    for token, filled in zip(frame, retagged, strict=True)
                    if token.tag.upos in DONOR_OF
                ]
                forced = _forced_positions(candidate, pack, slots, pools)
                return Produced(
                    candidates=[
                        Candidate(
                            text=candidate,
                            metrics={
                                "target_positions": float(len(targets)),
                                "forced_positions": float(forced),
                            },
                        )
                    ]
                )
