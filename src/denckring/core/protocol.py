"""The data contract. Report and Meta serialise to stable JSON for non-Python callers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Literal, Protocol, get_args, runtime_checkable

from pydantic import BaseModel, Field, computed_field

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


class Violation(BaseModel):
    """One place where a text fails a procedure."""

    rule: str
    offset: int | None = None
    found: str
    expected: str
    note: str | None = None


class Report(BaseModel):
    """The result of checking a text. `satisfied` is always `score == 1.0`."""

    procedure: str
    satisfied: bool
    score: float = Field(ge=0.0, le=1.0)
    violations: list[Violation] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


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
    """A catalogue entry. The single source of truth for a procedure's description."""

    id: str
    names: dict[Lang, str]
    definitions: dict[Lang, str]
    source: str
    family: Family
    attribution: Attribution
    checkability: Checkability
    attested: Attestation = "codified"
    aliases: list[str] = Field(default_factory=list)
    kind: Kind
    languages: list[Lang]
    requires: list[str] = Field(default_factory=list)
    #: What the *generator* needs, which is not what the checker needs.
    #: `anagram` checks with core alone and generates only with a word lexicon;
    #: one list could not say both, so the generator's requirement went
    #: undeclared and `missing` reported nothing. ADR 0002 makes `apply` the
    #: optional half, and this is the field that lets the optional half be
    #: honest about its own cost.
    apply_requires: list[str] = Field(default_factory=list)
    deterministic: bool = True
    prompt_hints: dict[Lang, str] = Field(default_factory=dict)
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

    def ascenders(self) -> frozenset[str]: ...

    def descenders(self) -> frozenset[str]: ...

    def exceeds_x_height(self, ch: str) -> bool: ...

    def syllable_count(self, word: str) -> tuple[int, bool]: ...

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
