"""Versioned caller-supplied bilingual data; structural validation only (ADR 0049)."""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, Json, field_validator, model_validator

from denckring.core.base import SourceParams
from denckring.core.protocol import Lang, LanguagePack
from denckring.lang.base import WORD_RE


def normalized(word: str) -> str:
    return unicodedata.normalize("NFC", word).casefold()


def words(text: str, pack: LanguagePack) -> list[str]:
    return [normalized(word) for word in pack.tokenize(unicodedata.normalize("NFC", text))]


def unique_json(value: Any) -> Any:
    """Reject duplicate JSON keys before Pydantic can discard one of them."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate data key: {key}")
            result[key] = item
        return result

    def constant(value: str) -> None:
        raise ValueError(f"non-finite JSON value: {value}")

    if not isinstance(value, str):
        raise ValueError("data must be a JSON string")
    json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    return value


def entries(table: dict[str, list[str]], *, glosses: bool) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for key, values in table.items():
        key = normalized(key)
        if WORD_RE.fullmatch(key) is None or key in result:
            raise ValueError("data keys must be distinct single tokens after normalization")
        if not values or any(not value.strip() for value in values):
            raise ValueError("every entry needs nonempty values")
        if glosses and any(not WORD_RE.search(value) for value in values):
            raise ValueError("each gloss must contain at least one word token")
        result[key] = values
    return result


class BilingualData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["supplied-bilingual-v1"]
    source_language: Lang
    target_language: Lang
    provenance: str = Field(
        min_length=1, description="Caller-declared origin; not independently verified."
    )

    @model_validator(mode="after")
    def distinct_languages(self) -> Self:
        if self.source_language == self.target_language:
            raise ValueError("source and target languages must differ")
        if not self.provenance.strip():
            raise ValueError("provenance must not be blank")
        return self


class GlossData(BilingualData):
    glosses: dict[str, list[str]] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_entries(self) -> Self:
        self.glosses = entries(self.glosses, glosses=True)
        return self


class PronunciationData(BilingualData):
    alphabet: list[str] = Field(min_length=1)
    source_pronunciations: dict[str, list[str]] = Field(min_length=1)
    target_pronunciations: dict[str, list[str]] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_entries(self) -> Self:
        if len(set(self.alphabet)) != len(self.alphabet) or any(
            not symbol or any(ch.isspace() for ch in symbol) for symbol in self.alphabet
        ):
            raise ValueError("alphabet must contain distinct nonempty symbols without whitespace")
        self.source_pronunciations = entries(self.source_pronunciations, glosses=False)
        self.target_pronunciations = entries(self.target_pronunciations, glosses=False)
        allowed = set(self.alphabet)
        for table in (self.source_pronunciations, self.target_pronunciations):
            if any(symbol not in allowed for values in table.values() for symbol in values):
                raise ValueError("pronunciations must use the declared shared alphabet")
        return self


class GlossParams(SourceParams):
    data: Json[GlossData] = Field(
        description="Versioned JSON containing source-token to target-gloss alternatives."
    )

    _unique = field_validator("data", mode="before")(unique_json)


class PronunciationParams(SourceParams):
    data: Json[PronunciationData] = Field(
        description="Versioned JSON with two pronunciation tables and a shared symbol alphabet."
    )
    max_distance: float = Field(
        ge=0,
        le=1,
        allow_inf_nan=False,
        description="Explicit maximum normalized symbol edit distance; no default.",
    )

    _unique = field_validator("data", mode="before")(unique_json)
