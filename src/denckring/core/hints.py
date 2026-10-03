"""Prompt hints as templates, and the one rule that renders them (ADR 0050).

A hint states the task in `str.format` placeholders — `{forbidden}`, not `"e"` —
so a caller who mints a parameter gets a prompt asking for the task the checker
will judge. Written for the defaults, a hint asked for one task while the checker
judged another, and neither half looked wrong on its own.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from string import Formatter
from typing import Any

from pydantic import BaseModel

from denckring.core.errors import UnsetHintParameter
from denckring.core.text import quoted_letters

#: Parameters no hint states, house-wide, each with the reason. Everything else a
#: row's checker accepts must appear in each of its hints or be named, with its
#: own reason, in that row's catalogue `hint_omits` — the guard in
#: `tests/test_prompt_hints.py` holds both halves.
#:
#: Kept to parameters whose meaning is the same on every row that has them. A
#: reason true only of some rows belongs on those rows, where the next person to
#: change one reads it.
UNSTATED_PARAMS: dict[str, str] = {
    "fold_diacritics": (
        "reading policy: decides how the checker reads an accented letter, not what "
        "the writer is asked to do"
    ),
    "unknown_rhyme": (
        "reading policy: decides what a word missing from the pronouncing dictionary "
        "means to the checker"
    ),
    "unknown_word": (
        "reading policy: decides what a word missing from the pronouncing dictionary "
        "means to the checker"
    ),
    "ambiguous_nouns": (
        "reading policy: decides what an unchanged word the dictionary lists means to the checker"
    ),
    "allow_identity": (
        "a strictness: no hint asks for the source back unchanged, and the setting "
        "refuses a copy only where another answer exists, so on a source that "
        "already meets the hint the copy may fail where another text passes"
    ),
    "source": (
        "material, not instruction: the text being transformed is given beside the "
        "prompt, and a hint quoting it whole would stop being a hint"
    ),
}


def placeholders(template: str) -> list[str]:
    """The field names a template uses, in order, repeats included."""
    return [name for _, name, _, _ in Formatter().parse(template) if name is not None]


#: How a parameter may declare it reads in a sentence, as
#: `json_schema_extra={"x-denckring-show": ...}` on its field. Closed, so a typo is
#: refused rather than rendered by the default rule. `letters` is a string of letters
#: read as a set: `"et"` renders `"e", "t"`, each letter quoted, because a set of
#: consonants quoted whole reads as the word `et` (audit B6, the bench's ruling R77).
SHOW_KEY = "x-denckring-show"
SHOW_KINDS: tuple[str, ...] = ("letters",)


def show_kinds(model: type[BaseModel]) -> dict[str, str]:
    """Each field of `model` that declares how it reads, mapped to its kind."""
    kinds: dict[str, str] = {}
    for name, field in model.model_fields.items():
        extra = field.json_schema_extra
        if isinstance(extra, Mapping) and SHOW_KEY in extra:
            kind = extra[SHOW_KEY]
            if kind not in SHOW_KINDS:
                raise ValueError(f"{model.__name__}.{name}: unknown {SHOW_KEY} {kind!r}")
            kinds[name] = str(kind)
    return kinds


def show(value: Any, kind: str | None = None) -> str:
    """How a parameter value reads in a sentence: the one rule for non-strings.

    A list or tuple joins its items with ", " (`[5, 7, 5]` reads `5, 7, 5`, not
    `[5, 7, 5]`); everything else is `str()`. A string is a sequence too, and is
    kept whole, unless its field declares `letters` (`SHOW_KINDS`), when each
    letter is quoted and the quotes joined with ", ". A template therefore leaves
    such a placeholder unquoted.
    """
    if kind == "letters" and isinstance(value, str):
        return quoted_letters(value)
    if isinstance(value, Sequence) and not isinstance(value, str):
        return ", ".join(str(item) for item in value)
    return str(value)


def render(
    procedure_id: str,
    template: str,
    values: Mapping[str, Any],
    kinds: Mapping[str, str] | None = None,
) -> str:
    """Fill `template` from `values`, refusing any placeholder whose value is `None`.

    `kinds` is `show_kinds` of the row's params model: how each field reads.
    """
    filled: dict[str, str] = {}
    for name in placeholders(template):
        if values.get(name) is None:
            raise UnsetHintParameter(procedure_id, name)
        filled[name] = show(values[name], (kinds or {}).get(name))
    return template.format(**filled)


def default_values(model: type[BaseModel]) -> dict[str, Any]:
    """Each parameter's default, for those that have one other than `None`."""
    defaults = {
        name: field.get_default(call_default_factory=True)
        for name, field in model.model_fields.items()
        if not field.is_required()
    }
    return {name: value for name, value in defaults.items() if value is not None}


def rendered_with_defaults(procedure_id: str, template: str, model: type[BaseModel]) -> str:
    """The template rendered from defaults if they fill every slot, else unchanged.

    What `describe` shows (ADR 0050). A hint whose slot has no default cannot be
    rendered without inventing a value, and a raw `{target}` beside the `params`
    schema that defines it is more honest than an invented one.
    """
    defaults = default_values(model)
    if all(name in defaults for name in placeholders(template)):
        return render(procedure_id, template, defaults, show_kinds(model))
    return template
