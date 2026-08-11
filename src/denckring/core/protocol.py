"""The data contract. Report and Meta serialise to stable JSON for non-Python callers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import ClassVar, Literal, Protocol, get_args, runtime_checkable

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
    aliases: list[str] = Field(default_factory=list)
    kind: Kind
    languages: list[Lang]
    requires: list[str] = Field(default_factory=list)
    deterministic: bool = True
    prompt_hints: dict[Lang, str] = Field(default_factory=dict)


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

    def syllables(self, word: str) -> list[str]: ...

    def nouns(self) -> Iterable[str]: ...
