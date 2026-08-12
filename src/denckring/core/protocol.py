"""The data contract. Report and Meta serialise to stable JSON for non-Python callers."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, ClassVar, Literal, Protocol, get_args, runtime_checkable

from pydantic import BaseModel, Field

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
    deterministic: bool = True
    prompt_hints: dict[Lang, str] = Field(default_factory=dict)


@runtime_checkable
class Constructive(Protocol):
    """A procedure that can generate, not merely validate.

    `apply` is optional by ADR 0002, so it is not on `BaseProcedure`. This
    protocol is how callers ask whether a given procedure has one, and it
    narrows the type at the same time.
    """

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any
    ) -> str: ...


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

    def rhyme_key(self, word: str) -> str: ...

    def rhyme_keys(self, word: str) -> list[str]: ...

    def stress_pattern(self, word: str) -> str: ...

    def stress_patterns(self, word: str) -> list[str]: ...

    def is_word(self, word: str) -> bool: ...

    def nouns(self) -> Sequence[str]: ...

    def noun_index(self, word: str) -> int | None: ...
