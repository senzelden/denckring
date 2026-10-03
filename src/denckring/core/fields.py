"""What a parameter is: its role in the task, and what kind of string it holds.

Every field of every params model declares both in its JSON Schema, as
`x-denckring-role` and (for a string) `x-denckring-kind`, so a caller that never
touches Python reads them from `describe(...).params` beside the type they qualify.

Before 0.3.2 a default of `None` was the only signal, and it meant five things: the
checker infers the value from the text (`tautogram.initial`), every unit
(`anaphora.minimum`), a value only `apply` reads, the pack's own dictionary
(`n_plus_7.dictionary`), or optional data (`arca_musarithmica.tonus`). A consumer
minting parameters had to tell them apart by reading prose, and kept a hand-written
list of reasons per parameter (audit C1). Likewise a string field was a bare
`{"type": "string"}` whether it held a letter, a set of letters, a word or a rhyme
scheme, so `forbidden` could not be drawn without knowing which row it was on
(audit C5).

Both sets are closed: a typo is refused when the schema is read, not published.
"""

from __future__ import annotations

import types
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

ROLE_KEY = "x-denckring-role"
KIND_KEY = "x-denckring-kind"

Role = Literal[
    "task",
    "inferred",
    "policy",
    "leniency",
    "switch",
    "material",
    "tolerance",
    "budget",
    "apply_only",
]

#: Each role, and what it tells a caller writing a prompt for the row. The reason a
#: hint may leave a parameter unstated is its role's (`core.hints.unstated`): a hint
#: must state every `task` and `inferred` parameter, and may leave any other unstated.
ROLES: dict[str, str] = {
    "task": "What the writer is asked to do. Every hint states it.",
    "inferred": (
        "Part of the task when set. Unset (`None`), the checker reads it off the text: "
        "`tautogram` takes the first word's initial. A hint states it, so a caller "
        "rendering one sets it."
    ),
    "policy": (
        "reading policy: decides how the checker reads the text (an accented letter, a "
        "word the dictionary lacks), not what the writer is asked to do"
    ),
    "leniency": (
        "a leniency: admits texts the strict form refuses, and a text in the strict "
        "form satisfies either setting, so a hint asking for the strict form is right "
        "under both"
    ),
    "switch": (
        "a switch that adds a requirement the default does not make; a caller who "
        "turns it on states it in the prompt"
    ),
    "material": (
        "material, not instruction: data the checker reads beside the text (the source, "
        "a table, a dictionary, a device), given to the writer rather than quoted"
    ),
    "tolerance": (
        "a tolerance: how far a measured quantity may stray from the task and still "
        "pass, which a writer cannot aim at"
    ),
    "budget": ("a budget: bounds the work a call does; past it the call is refused, not judged"),
    "apply_only": "read by the generator alone; `check` never sees it",
}

Kind = Literal[
    "letter",
    "letters",
    "vowel",
    "vowels",
    "consonant",
    "word",
    "phrase",
    "name",
    "scheme",
    "metre",
    "digits",
    "text",
    "document",
    "id",
]

#: What a string parameter holds, so a caller can draw one without knowing the row.
#: For a list of strings, the kind is each item's.
KINDS: dict[str, str] = {
    "letter": "One letter of the language's alphabet.",
    "letters": "A set of letters, written together: `et` is `e` and `t`, not a word.",
    "vowel": "One vowel letter of the language.",
    "vowels": "A set of vowel letters, written together.",
    "consonant": "One consonant letter of the language.",
    "word": "One word.",
    "phrase": "A word or several, read as a sequence of letters or words.",
    "name": "A person's name.",
    "scheme": (
        "A rhyme scheme: one letter per line, lines sharing a letter rhyme and lines "
        "with different letters do not (`ABAB`)."
    ),
    "metre": "A stress pattern per line: `0` an unstressed syllable, `1` a stressed one.",
    "digits": "Digits entered on a calculator display.",
    "text": "A passage of prose or verse.",
    "document": "A structured data document the row parses (JSON).",
    "id": (
        "A key from a fixed set: a shipped device, figure or domain, a procedure id, or "
        "a key the supplied data defines."
    ),
}


#: A list of the values a parameter's form exists for, where the checker accepts
#: others and fails them rather than refusing them (`quenina.n`). Not a JSON Schema
#: `enum`, which would refuse values `check` accepts today; a caller drawing a value
#: draws from this (audit B5). JSON Schema keywords that do validate (`enum`,
#: `pattern`, `minLength`) appear on a field only where `check` already refuses every
#: value they rule out, which `tests/test_drawable_schemas.py` holds.
VALID_KEY = "x-denckring-valid"


def param(
    role: Role, kind: Kind | None = None, *, valid: Sequence[Any] | None = None, **schema: Any
) -> dict[str, Any]:
    """The `json_schema_extra` a field declares: its role, its kind, and any more keys.

    `valid` is written as `VALID_KEY`. `schema` carries further JSON Schema for the
    property (`x-denckring-show`, `examples`, `enum`, ...), written as given.
    """
    extra: dict[str, Any] = {ROLE_KEY: role}
    if kind is not None:
        extra[KIND_KEY] = kind
    if valid is not None:
        extra[VALID_KEY] = list(valid)
    extra.update(schema)
    return extra


def _declared(model: type[BaseModel], key: str, closed: Mapping[str, str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, field in model.model_fields.items():
        extra = field.json_schema_extra
        if isinstance(extra, Mapping) and key in extra:
            value = extra[key]
            if value not in closed:
                raise ValueError(f"{model.__name__}.{name}: unknown {key} {value!r}")
            found[name] = str(value)
    return found


def roles(model: type[BaseModel]) -> dict[str, str]:
    """Each field of `model` that declares a role, mapped to it."""
    return _declared(model, ROLE_KEY, ROLES)


def kinds(model: type[BaseModel]) -> dict[str, str]:
    """Each field of `model` that declares a string kind, mapped to it."""
    return _declared(model, KIND_KEY, KINDS)


def holds_strings(annotation: Any) -> bool:
    """Whether a field's type is a free string, or a list of them, optionally `None`.

    A `Literal` of strings is not free: its schema already lists the values, so it
    declares no kind. A dict keyed by strings is a mapping, not a string.
    """
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        return any(holds_strings(arg) for arg in get_args(annotation) if arg is not type(None))
    if annotation is str:
        return True
    if origin is list:
        return get_args(annotation) == (str,)
    return False
