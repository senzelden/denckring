"""Prompt hints as templates, and the one rule that renders them (ADR 0050).

A hint states the task in `str.format` placeholders — `{forbidden}`, not `"e"` —
so a caller who mints a parameter gets a prompt asking for the task the checker
will judge. Written for the defaults, a hint asked for one task while the checker
judged another, and neither half looked wrong on its own.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from string import Formatter
from typing import Any

from pydantic import BaseModel

from denckring.core.errors import UnsetHintParameter
from denckring.core.fields import ROLES, kinds, roles
from denckring.core.protocol import Lang, LanguagePack
from denckring.core.text import quoted_letters

#: The roles whose parameters every hint must state (`core.fields.ROLES`): what the
#: writer is asked to do, and what the checker would otherwise read off the text.
STATED_ROLES: frozenset[str] = frozenset({"task", "inferred"})


def unstated(model: type[BaseModel], omits: Mapping[str, str]) -> dict[str, str]:
    """Each parameter of `model` a hint may leave out, mapped to the reason.

    Derived from each field's role (audit C1): a parameter whose role is not in
    `STATED_ROLES` is left out of the template for its role's reason, so a new
    reading policy or leniency needs no entry anywhere. The excuse holds at the
    default only: set otherwise, `settings` states the parameter after the hint.
    `omits` is the row's catalogue `hint_omits`: the `task` parameters its hints
    still leave out, each with its reason (a composite's own parameters, a
    ladder's end). The guards in
    `tests/test_prompt_hints.py` hold every other parameter to every hint, and
    `hint_omits` to naming only parameters the roles do not already excuse.
    """
    reasons = {name: ROLES[role] for name, role in roles(model).items() if role not in STATED_ROLES}
    reasons.update(omits)
    return reasons


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


#: The quotation marks a hint in each language puts round a letter, as its own
#: templates quote a placeholder: a French hint reading `"b", "c"` mixes two styles.
QUOTES: dict[str, tuple[str, str]] = {
    "en": ('"', '"'),
    "de": ("\u201e", "\u201c"),
    "fr": ("\u00ab ", " \u00bb"),
}

#: The string kinds (`core.fields.KINDS`) that name letters, which a checker compares
#: folded when `fold_diacritics` is on.
LETTER_KINDS: frozenset[str] = frozenset({"letter", "letters", "vowel", "vowels", "consonant"})


def as_compared(
    values: Mapping[str, Any], model: type[BaseModel], pack: LanguagePack
) -> dict[str, Any]:
    """`values` with each letter given as the checker compares it.

    Under `fold_diacritics`, `forbidden="é"` forbids every `e`: a hint stating `é`
    beside its own sentence that `é` counts as `e` asked for one thing and was judged
    on another. So a letter-kind value is shown folded, each letter of a set once, in
    the order given, as `consonantal_lipogram` names it in a violation. A letter that
    folds to two (`ß`) is left as given: the checker refuses it, and the hint should
    not pretend otherwise. Rendering only; `check` folds for itself.
    """
    shown = dict(values)
    if not shown.get("fold_diacritics"):
        return shown
    for name, kind in kinds(model).items():
        value = shown.get(name)
        if kind not in LETTER_KINDS or not isinstance(value, str):
            continue
        folded = [pack.fold_diacritics(ch) for ch in value]
        if all(len(letter) == 1 for letter in folded):
            shown[name] = "".join(dict.fromkeys(folded) if kind == "letters" else folded)
    return shown


def show(value: Any, kind: str | None = None, lang: Lang = "en") -> str:
    """How a parameter value reads in a sentence: the one rule for non-strings.

    A list or tuple joins its items with ", " (`[5, 7, 5]` reads `5, 7, 5`, not
    `[5, 7, 5]`); everything else is `str()`. A string is a sequence too, and is
    kept whole, unless its field declares `letters` (`SHOW_KINDS`), when each
    letter is quoted and the quotes joined with ", ". A template therefore leaves
    such a placeholder unquoted.
    """
    if kind == "letters" and isinstance(value, str):
        return quoted_letters(value, QUOTES[lang])
    if isinstance(value, Sequence) and not isinstance(value, str):
        return ", ".join(str(item) for item in value)
    return str(value)


def render(
    procedure_id: str,
    template: str,
    values: Mapping[str, Any],
    kinds: Mapping[str, str] | None = None,
    lang: Lang = "en",
) -> str:
    """Fill `template` from `values`, refusing any placeholder whose value is `None`.

    `kinds` is `show_kinds` of the row's params model: how each field reads. `lang`
    is the template's language, which picks the quotation marks.
    """
    filled: dict[str, str] = {}
    for name in placeholders(template):
        if values.get(name) is None:
            raise UnsetHintParameter(procedure_id, name)
        filled[name] = show(values[name], (kinds or {}).get(name), lang)
    return template.format(**filled)


def settings(
    model: type[BaseModel],
    values: Mapping[str, Any],
    shown: Mapping[str, Any],
    carried: Collection[str],
    lang: Lang = "en",
) -> list[str]:
    """One line per parameter set off its default that the prompt does not otherwise carry.

    A role may excuse a parameter from a template (`unstated`), but only at its
    default: set otherwise, it changes what the checker judges, and a prompt that
    drops it asks for the default task while the text is graded on another (the
    final 0.3.2 review's I3: `eodermdrome` with `min_letters=12` read as accepting
    `dead`). So each such parameter is appended as `- name = value: description`,
    in field order, the value read by `show` from `shown` and the description the
    field's own, which is English in every language. `values` are the parsed
    parameters, compared with each default; `carried` names the parameters the
    template states, or that another line states. A parameter with no default is
    never listed: a required `task` parameter is in every template, and required
    material is given to the writer rather than quoted. With every value at its
    default the list is empty, so the hint is byte for byte what it was.
    """
    kinds = show_kinds(model)
    lines: list[str] = []
    for name, field in model.model_fields.items():
        if name in carried or field.is_required():
            continue
        if values.get(name) == field.get_default(call_default_factory=True):
            continue
        value = show(shown.get(name), kinds.get(name), lang)
        description = (field.description or "").strip()
        lines.append(f"- {name} = {value}: {description}" if description else f"- {name} = {value}")
    return lines


def default_values(model: type[BaseModel]) -> dict[str, Any]:
    """Each parameter's default, for those that have one other than `None`."""
    defaults = {
        name: field.get_default(call_default_factory=True)
        for name, field in model.model_fields.items()
        if not field.is_required()
    }
    return {name: value for name, value in defaults.items() if value is not None}


def rendered_with_defaults(
    procedure_id: str, template: str, model: type[BaseModel], lang: Lang = "en"
) -> str:
    """The template rendered from defaults if they fill every slot, else unchanged.

    What `describe` shows (ADR 0050). A hint whose slot has no default cannot be
    rendered without inventing a value, and a raw `{target}` beside the `params`
    schema that defines it is more honest than an invented one.
    """
    defaults = default_values(model)
    if all(name in defaults for name in placeholders(template)):
        return render(procedure_id, template, defaults, show_kinds(model), lang)
    return template
