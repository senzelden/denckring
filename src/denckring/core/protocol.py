"""The data contract. Report and Meta serialise to stable JSON for non-Python callers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Literal, NamedTuple, Protocol, get_args, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from denckring.core.provenance import Provenance

Lang = Literal["en", "de", "fr"]
Kind = Literal["constructive", "restrictive", "both"]

#: What a procedure operates on. Closed, so an invalid family is a validation
#: error rather than a typo that silently creates a ninth group.
Family = Literal[
    "letter",
    "word",
    "syntax",
    "form",
    "permutation",
    "procedural",
    "translation",
    "visual",
]
#: Runtime view of `Family`, for validation messages and the CLI.
FAMILIES: tuple[str, ...] = get_args(Family)

#: How an entry's source was established. `primary` names an author, work and
#: year the entry stands behind; `reference` means the form is attested in a
#: standard work rather than traced to an origin; `traditional` means no single
#: origin exists to name.
Attribution = Literal["primary", "reference", "traditional"]

#: Whether a procedure admits a mechanical check at all. `self` is decidable
#: from the text and its parameters; `source` needs the text it was made from;
#: `none` means no computable acceptance criterion exists — the row is
#: catalogued because the form belongs in an honest survey of the field, not as
#: a backlog item. ADR 0002 keeps `none` rows permanently unregistered.
#: Whether anyone ever set the procedure down as a rule. Distinct from
#: `Attribution`, which records how the *source* was established: Harsdörffer
#: wrote instructions for his rings, the sonnet was codified by prosodists
#: rather than declared by an author, and Jean Paul's Ideenwürfeln is a rule
#: reconstructed from a notebook. Conservative by design — using a form is not
#: stating it, so Perec writing La Disparition does not make the lipogram
#: author-stated.
Attestation = Literal["author-stated", "codified", "reconstruction"]
ATTESTATIONS: tuple[str, ...] = get_args(Attestation)

Checkability = Literal["self", "source", "none"]
CHECKABILITIES: tuple[str, ...] = get_args(Checkability)

#: Which acceptance test an entry answers to (ADR 0033). A `verfahren` is accepted
#: when it runs and yields text a checker scores; an `instrument` is accepted when its
#: mechanism is faithfully formalised and sourced, and may produce no text at all —
#: temurah, Ifá, the 231 gates. The German word stays because `procedure` already names
#: both layers everywhere else in this package, from the YAML key to the CLI.
Layer = Literal["verfahren", "instrument"]
LAYERS: tuple[str, ...] = get_args(Layer)


class Violation(BaseModel):
    """One place where a text fails a procedure."""

    rule: str
    #: Where in the checked text, as a character index. `len(text)` means "at the
    #: end": something the text ran out before supplying (a missing tail in
    #: `every_nth_word`, `slenderizing`, `column_reading`, `haikuization`), placed
    #: where it would go, so `text[offset]` is not always a valid index. `None`
    #: means the violation has no place in the text (`missing_part`).
    offset: int | None = None
    found: str
    expected: str
    note: str | None = None


class Evidence(BaseModel):
    """One measurement a verdict rests on, and how it was obtained.

    `metrics["estimated_words"]` has carried the uncertainty since the beginning,
    and it carries it as a single number: a haiku report could say that two of its
    words were guessed and never which two. A reader repairing the line, or an
    auditor deciding whether to trust the verdict, needs the second thing.

    `basis` is a closed set rather than a confidence score. The pack knows whether
    a count came out of a dictionary or was estimated, and that is the whole of
    what this field says. English has two estimates since 0.3.2, the spelling
    heuristic and a reading through a dictionary stem (`awakes` from `awake`),
    and both report `estimated` without saying which. Attaching `0.94` to either
    would invent a precision no measurement here supports, which is what the
    review that asked for this warned against in its own last paragraph.

    `ambiguous` (0.4.0, ADR 0054) is the dictionary listing more than one reading of
    the word, every one of which the checker accepted: `every` counted as 3 or 2
    syllables, `bog` rhyming on either vowel. Looked up, not estimated, so it does
    not make a report `estimated`; it says the verdict may rest on a variant rather
    than the first form. `dictionary` now means the checker read the word one way.

    `scope` exists because the answer is not always about a word. French counts a
    *line* — a final mute e elides or counts depending on what follows, so summing
    citation forms undercounts systematically (ADR 0034) — and there is no
    per-word breakdown to report. Saying so is better than manufacturing one.
    """

    subject: str
    scope: Literal["word", "line"] = "word"
    offset: int | None = None
    value: str
    basis: Literal["dictionary", "ambiguous", "estimated"]


class Report(BaseModel):
    """The result of checking a text. `satisfied` is always `score == 1.0`,
    enforced below rather than left as a constructor convention (P2-02)."""

    #: Re-runs the `satisfied`/`score` invariant on attribute assignment, not
    #: just at construction (whole-branch review finding: `model_validator`
    #: alone does not). `model_copy(update=...)` — how `provenance` is set
    #: after construction in `core/base.py` — is unaffected either way, since
    #: it never runs validators regardless of this setting.
    model_config = ConfigDict(validate_assignment=True)

    procedure: str
    satisfied: bool
    score: float = Field(ge=0.0, le=1.0)
    violations: list[Violation] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    #: The measurements behind the verdict, where a procedure can name them.
    #: Empty on the exactly decidable rows, which have nothing to explain: a
    #: lipogram's violation already carries the offending character and its
    #: offset. It is the syllabic and phonetic rows, where a number was estimated,
    #: that owed the reader an account of which words they guessed at.
    evidence: list[Evidence] = Field(default_factory=list)
    #: How the verdict was reached: versions, pack, and the policies in force.
    #: An added field, which the README's stability promise permits, and optional
    #: because a procedure may build a `Report` itself — `pangram` does — and the
    #: stamp is applied once in `BaseProcedure.check` rather than in each of the
    #: hundred and twenty-two places a report is constructed.
    provenance: Provenance | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def estimated(self) -> bool:
        """Whether the verdict rests on anything this install estimated or left unjudged.

        The one signal a caller deciding to leave a verdict unscored should read (audit
        B8). Until 0.3.2 it had two places to look and neither was enough alone:
        `metrics["estimated_words"]` is not under the stability promise, and on some
        rows counts what no `Evidence` records (`proteus_verse` and `spoonerism` count
        words read from spelling, `definitional_expansion` words no gloss resolved);
        `evidence` records what the metric does not (the rhyme endings of `clerihew`
        and `rondeau`, which report no such metric). True when either says so. A word
        left unjudged counts: `definitional_expansion` scores only the words its
        glosses resolve, so its verdict covers less of the text than it reads as
        covering, and `describe` calls its reading heuristic (ADR 0054). An
        `ambiguous` basis does not count: the word was looked up. `multiple_constraint`
        carries its constraints' evidence and counts, so a composite is estimated
        when any constraint inside it is.

        Computed, not stored, so it cannot disagree with the report it describes,
        and added beside the other fields rather than changing any of them. It reads
        a metrics key the library owns; a caller reads this instead. N+7's
        `ambiguous_words` is not an estimate: it counts words a reading policy
        (`ambiguous_nouns`) decides, and the verdict states that policy.
        """
        return any(item.basis == "estimated" for item in self.evidence) or (
            self.metrics.get("estimated_words", 0.0) > 0
        )

    @model_validator(mode="after")
    def _satisfied_matches_score(self) -> Report:
        if self.satisfied != (self.score == 1.0):
            raise ValueError(
                f"satisfied={self.satisfied} disagrees with score={self.score} "
                f"(satisfied must equal score == 1.0)"
            )
        return self


class Candidate(BaseModel):
    """One result, with whatever the generator knows about it.

    `Production.texts` was a list of strings, and for most generators that is
    still the whole truth. `anagram` is the exception ADR 0026 anticipated in
    writing: it ranks its covers by the SCOWL band of their least common word,
    and a bare string cannot carry the number the ranking was computed from. A
    caller shown `room dirty` ahead of `morty dior` deserves to see why, rather
    than trusting the order. `denckring` joined it under ADR 0031's mask, which
    marks each spun word attested or neglected.

    No count of which generators are in which case is kept here. One was, and it
    was wrong within two chapters.

    `metrics` is open rather than a fixed set of fields because what a generator
    knows is generator-specific, and a schema listing every score any procedure
    might ever have would be a schema nobody could satisfy.
    """

    text: str
    metrics: dict[str, float] = Field(default_factory=dict)


class Produced(BaseModel):
    """What `_produce` hands the spine: its candidates, and whether it gave up.

    `truncated` here is the generator's own, and is not the same statement as
    `Production.truncated`. The spine can see that `max_results` capped a result
    set; it cannot see that a search abandoned its own budget, because that makes
    the set *smaller* rather than larger. `anagram`'s node budget is the case ADR
    0026's spec named in advance as needing this.
    """

    candidates: list[Candidate]
    truncated: bool = False


class Production(BaseModel):
    """What a generator turned out. `Report`'s counterpart for the other half.

    `check` has returned a structured verdict since the beginning while `apply`
    returned a bare string, so a generator that found several valid answers had
    one place to put one of them. `paragram` scores every candidate it finds and
    discards all but the best; `anagram` found 47 covers of `dormitory` behind
    the one `apply` returns. This is where the rest go.
    """

    procedure: str
    #: Best first — `apply` returns `texts[0]`, so the order is the contract.
    #: Never empty: a generator with nothing to return raises, and an empty list
    #: would be a fourth way of saying a failure that has three honest names.
    #: `min_length=1` makes that a validation error naming the field rather than
    #: a bare `IndexError` from `apply`'s `texts[0]`.
    candidates: list[Candidate] = Field(min_length=1)
    #: Whether what was returned is less than what there is, under either of the
    #: two events that can make it so: `max_results` capped the result set, or
    #: the generator abandoned its own search budget and said so on
    #: `Produced.truncated` (ADR 0027). Only the first is visible from the
    #: spine, which is why the second is reported rather than inferred. Without
    #: it a truncated search is indistinguishable from an exhaustive one.
    #: On the ten rows that draw at random this reads narrowly: a drawing
    #: generator returns one sample per call, so `truncated` is always false and
    #: `metrics["found"]` always 1.0 — "everything the search found", not
    #: "everything the procedure could produce". `texts` is not used for *n*
    #: draws of one procedure; asking for a second sample means calling again
    #: with another seed.
    truncated: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
    #: The counterpart of `Report.provenance`, and the only place the seed a
    #: drawing generator used is recoverable: `seed` is an input parameter, so
    #: `apply --seed 7 --json` printed an object that did not contain 7 and a
    #: caller who had not kept it could not reproduce the draw.
    provenance: Provenance | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def texts(self) -> list[str]:
        """The candidates' texts, in the same order.

        A `computed_field` and not a plain `@property`: `apply --json` and the
        MCP surface both read `texts` out of `model_dump()`, and a plain property
        is absent from it. Kept rather than removed because it is the shape every
        existing consumer already reads, and ADR 0026 made `texts[0]` the
        definition of `apply`.
        """
        return [candidate.text for candidate in self.candidates]


class Meta(BaseModel):
    """A catalogue entry. The single source of truth for a procedure's description.

    Frozen, with its list-shaped fields as tuples: catalogue.get() returns the
    same cached object to every caller (P2-01), so a mutable Meta let one
    caller's introspection silently change what a registered procedure
    requires for every future check() call. `names`, `definitions` and
    `prompt_hints` (and `hint_omits`) stay plain dicts — no demonstrated mutation path reached
    them, and freezing a dict field needs a different mechanism than a tuple
    swap; that residual is deliberate, not overlooked.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    names: dict[Lang, str]
    definitions: dict[Lang, str]
    source: str
    family: Family
    attribution: Attribution
    checkability: Checkability
    #: Which of the two acceptance tests this row answers to (ADR 0033). Defaults
    #: to `verfahren`, which is what every row written before the split is, and what
    #: the five-part coverage line has always counted.
    layer: Layer = "verfahren"
    attested: Attestation = "codified"
    aliases: tuple[str, ...] = Field(default_factory=tuple)
    kind: Kind
    languages: tuple[Lang, ...]
    requires: tuple[str, ...] = Field(default_factory=tuple)
    #: What the *generator* needs, which is not what the checker needs.
    #: `anagram` checks with core alone and generates only with a word lexicon;
    #: one list could not say both, so the generator's requirement went
    #: undeclared and `missing` reported nothing. ADR 0002 makes `apply` the
    #: optional half, and this is the field that lets the optional half be
    #: honest about its own cost.
    apply_requires: tuple[str, ...] = Field(default_factory=tuple)
    #: Whether the form, as catalogued, fixes its output: false where it leaves the
    #: result to chance or to the writer (`cut_up`, `homophonic_translation`). A claim
    #: about generation, read from the form's definition rather than derived from this
    #: install's `apply`: most implemented rows marked false have no generator, and
    #: rows whose `apply` draws from a `seed` are not all marked false
    #: (`arca_musarithmica` and `denckring` are true). It says nothing about `check`,
    #: which is deterministic on every row: the same text, language and parameters give
    #: the same `Report` (`tests/test_invariants.py`). To know whether a generator
    #: draws, look for `seed` among its apply params; the same seed repeats the draw.
    deterministic: bool = True
    #: Whether `check` passes one text for a given source and parameters: the text
    #: `apply` returns, as the checker reads it (case and spacing aside). True for the
    #: rows that compute their answer from the source (`every_nth_word`,
    #: `slenderizing`), false where the writer chooses (`anagram`, `cut_up`). A caller
    #: grading a transform can then score against one answer (audit C4).
    #: `n_plus_7` is false: its default `ambiguous_nouns="free"` accepts a listed word
    #: left unchanged, so more than one text passes. `tests/test_suitability.py`
    #: holds each row flagged true to failing every text that differs in its words.
    unique_answer: bool = False
    #: Material a verdict depends on that the reader of a prompt cannot see unless the
    #: caller prints it: a parameter whose default is shipped data (`n_plus_7`'s
    #: `dictionary`, the pack's whole noun list; `denckring`'s `device`), or a
    #: required capability whose data decides the answer (`lexicon.glosses`). Each
    #: entry names the parameter or the capability. A prompt asking for such a row
    #: either supplies its own material and prints it, or is asking for an answer no
    #: writer can derive (audit C4).
    hidden_material: tuple[str, ...] = Field(default_factory=tuple)
    #: `str.format` templates over the row's parameters (ADR 0050). Read them
    #: through `denckring.prompt_hint`, or `describe`, never raw: a raw hint may
    #: still hold a `{placeholder}`.
    prompt_hints: dict[Lang, str] = Field(default_factory=dict)
    #: Task parameters this row's hints deliberately do not state, each with its
    #: reason. Every other unstated parameter is excused by its role
    #: (`x-denckring-role`, `core.hints.unstated`), so this names only what a role
    #: cannot explain; anything a role does not excuse and this does not name must
    #: appear in every hint (ADR 0050).
    hint_omits: dict[str, str] = Field(default_factory=dict)
    #: Contested figures, reception history and caveats — anything true about the
    #: entry that is not part of what the procedure *is*. Keeping it out of
    #: `definitions` is what lets a definition stay a definition.
    notes: str | None = None


@runtime_checkable
class Constructive(Protocol):
    """A procedure that can generate, not merely validate.

    `apply` is optional by ADR 0002, so it is not on `BaseProcedure`. This
    protocol is how callers ask whether a given procedure has one, and it
    narrows the type at the same time.

    `seed` was an explicit keyword here and is now an ordinary parameter on
    `SeedParams`, carried by the ten procedures that draw. A keyword named in
    this signature binds before `**params` and so can never be validated, which
    is what made `seed` unvalidatable for all 27.

    `produce` joined `apply` here for the same reason: `runtime_checkable`
    makes `isinstance` check method presence only, and every
    `ConstructiveProcedure` inherits both from the base class, so the set of
    procedures this protocol matches is unchanged by adding the second name.
    """

    def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str: ...

    def produce(self, text: str, *, lang: Lang = "en", **params: Any) -> Production: ...


#: UD's `VerbForm` feature, which is the one distinction `verbless_prose` turns
#: on: a finite verb is barred where a participle is the material the form is
#: written out of. `None` for everything that is not a verb or auxiliary.
VerbForm = Literal["Fin", "Part", "Inf", "Ger", "Sup", "Conv"]


class PosTag(NamedTuple):
    """One token's reading in its sentence.

    `known` is the honesty field and the reason this is a triple rather than a
    pair. A tagger answers for every token, including one it has never seen, by
    falling back on suffix and shape features — so unlike `syllable_count`'s
    `exact` there is no tier at which the answer is looked up rather than
    modelled. What can be said is whether the form was in the training data at
    all, and a row that reports a violation on a token where it was not must say
    so. ADR 0045.
    """

    #: UD universal POS: VERB, AUX, NOUN, ADJ, ADV, PRON, DET, ADP, ...
    upos: str
    verb_form: VerbForm | None
    known: bool


@runtime_checkable
class LanguagePack(Protocol):
    """Per-language behaviour.

    A pack implements every method here, but one whose capability it does not
    declare must raise `MissingCapability` rather than approximate. `word_spans`,
    `alphabet`, `vowels`, `ascenders` and `descenders` go beyond the original
    four-method sketch: violations need character offsets, and the prisoner's
    constraint needs glyph shapes.
    """

    lang: ClassVar[Lang]
    capabilities: ClassVar[frozenset[str]]
    word_re: ClassVar[re.Pattern[str]]

    def tokenize(self, text: str) -> list[str]: ...

    def word_spans(self, text: str) -> list[tuple[int, str]]: ...

    def fold_diacritics(self, ch: str) -> str: ...

    def alphabet(self) -> str: ...

    def vowels(self) -> frozenset[str]: ...

    def vowel_inventory(self) -> frozenset[str]: ...

    def ascenders(self) -> frozenset[str]: ...

    def descenders(self) -> frozenset[str]: ...

    def exceeds_x_height(self, ch: str) -> bool: ...

    def syllable_count(self, word: str) -> tuple[int, bool]: ...

    def line_syllables(self, line: str) -> tuple[int, int]: ...

    def syllables(self, word: str) -> list[str]: ...

    def phonemes(self, word: str) -> list[str]: ...

    def is_vowel_phoneme(self, phoneme: str) -> bool: ...

    def rhyme_key(self, word: str) -> str: ...

    def rhyme_keys(self, word: str) -> list[str]: ...

    def stress_pattern(self, word: str) -> str: ...

    def stress_patterns(self, word: str) -> list[str]: ...

    def is_word(self, word: str) -> bool: ...

    def glosses(self, word: str) -> Sequence[str]: ...

    def nouns(self) -> Sequence[str]: ...

    def noun_index(self, word: str) -> int | None: ...

    def graded_words(self) -> Mapping[str, int]: ...

    def pos_tags(self, words: Sequence[str]) -> list[PosTag]: ...


class ProverbCorpus(Protocol):
    """Optional corpus capability; does not widen the stable LanguagePack contract."""

    def proverbs(self) -> Sequence[tuple[str, str]]: ...


class LexicalRelations(Protocol):
    """Optional exact dictionary relations, not a contextual semantic oracle."""

    def synonyms(self, word: str) -> Sequence[str]: ...

    def antonyms(self, word: str) -> Sequence[str]: ...
