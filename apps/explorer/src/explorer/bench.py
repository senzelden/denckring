"""Running a procedure, and marking up the result.

Forms are built from each procedure's `params_schema()`. That JSON Schema has
been on the protocol since Batch 1 for the sake of callers who never touch
Python; this is the first thing to actually consume it.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any, cast, get_args

from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DenckringError
from denckring.core.protocol import Constructive, Lang, LanguagePack, Report
from denckring.core.registry import get
from denckring.eval import harness
from denckring.lang import get_pack, installed_languages

#: Rendered inline, so an offset that lands past the end of the text is a bug we
#: would rather see than swallow.
MARK_OPEN = '<mark class="hit">'
MARK_CLOSE = "</mark>"


@dataclass
class Field:
    """One parameter, ready to render as an input."""

    name: str
    kind: str
    default: Any
    description: str
    required: bool
    choices: list[str] = field(default_factory=list)
    #: For `kind == "array"`, the type of one entry. Everything else ignores it.
    #: It exists because `coerce` cast every array entry with `int`, which was
    #: right for the only array field there was when it was written
    #: (`syllable_count.pattern`) and wrong for all three that have arrived
    #: since — `multiple_constraint.constraints` and `n_plus_7`/`s_plus_7`'s
    #: `dictionary` are lists of words, and a word is not a number.
    item_kind: str = "string"

    @property
    def control(self) -> str:
        if self.choices:
            return "select"
        if self.kind == "boolean":
            return "checkbox"
        if self.kind == "integer":
            return "number"
        if self.name == "source":
            return "textarea"
        return "text"


def _choices(spec: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Pull enum values out, following a $ref when Pydantic emits one."""
    for branch in spec.get("anyOf", []) or [spec]:
        if "enum" in branch:
            return [str(v) for v in branch["enum"]]
        ref = branch.get("$ref", "")
        if ref.startswith("#/$defs/"):
            target = schema.get("$defs", {}).get(ref.split("/")[-1], {})
            if "enum" in target:
                return [str(v) for v in target["enum"]]
    return []


def _kind(spec: dict[str, Any]) -> str:
    if "type" in spec:
        return str(spec["type"])
    for branch in spec.get("anyOf", []):
        if branch.get("type") not in (None, "null"):
            return str(branch["type"])
    return "string"


def _item_kind(spec: dict[str, Any]) -> str:
    """The type of one entry of an array field.

    Follows `anyOf` for the same reason `_kind` does: an optional list arrives
    as `[{"type": "array", "items": …}, {"type": "null"}]`, and the branch that
    carries the items is not the first one in every schema Pydantic emits.
    """
    for branch in [spec, *spec.get("anyOf", [])]:
        items = branch.get("items")
        if isinstance(items, dict) and "type" in items:
            return str(items["type"])
    return "string"


def _fields_from(schema: dict[str, Any]) -> list[Field]:
    required = set(schema.get("required", []))
    fields = []
    for name, spec in schema.get("properties", {}).items():
        fields.append(
            Field(
                name=name,
                kind=_kind(spec),
                default=spec.get("default"),
                description=spec.get("description", ""),
                required=name in required,
                choices=_choices(spec, schema),
                item_kind=_item_kind(spec),
            )
        )
    # Required parameters first: they are what the caller must supply.
    return sorted(fields, key=lambda f: (not f.required, f.name))


def fields_for(procedure_id: str) -> list[Field]:
    """The parameter form, derived from the procedure's own JSON Schema."""
    return _fields_from(get(procedure_id).params_schema())


def coerce(fields: list[Field], form: dict[str, str]) -> dict[str, Any]:
    """Turn form strings into the types the schema asks for.

    An empty optional field is dropped rather than sent as "", so the
    procedure's own default applies — sending "" would be a different request.
    """
    params: dict[str, Any] = {}
    for spec in fields:
        raw = form.get(spec.name)
        if spec.kind == "boolean":
            params[spec.name] = raw is not None
            continue
        if raw is None or raw == "":
            continue
        if spec.kind == "integer":
            params[spec.name] = int(raw)
        elif spec.kind == "array":
            parts = raw.replace(",", " ").split()
            if spec.item_kind == "integer":
                params[spec.name] = [int(part) for part in parts]
            else:
                params[spec.name] = parts
        else:
            params[spec.name] = raw
    return params


def mark_up(text: str, report: Report) -> str:
    """The text with the offending characters marked, as on a proof.

    This is what `Violation.offset` has been carrying since the first spec.
    Violations without an offset — a missing letter, a wrong line count — have
    nothing to point at and are listed in the margin instead.
    """
    hits = sorted({v.offset for v in report.violations if v.offset is not None})
    if not hits:
        return html.escape(text)
    pieces: list[str] = []
    cursor = 0
    for offset in hits:
        if offset < cursor or offset >= len(text):
            continue
        pieces.append(html.escape(text[cursor:offset]))
        pieces.append(MARK_OPEN + html.escape(text[offset]) + MARK_CLOSE)
        cursor = offset + 1
    pieces.append(html.escape(text[cursor:]))
    return "".join(pieces)


def examples_for(procedure_id: str) -> list[dict[str, Any]]:
    """The golden fixtures, offered as one-click starting points."""
    return [
        {
            "name": case.name,
            "lang": case.lang,
            "text": case.text,
            "params": case.params,
            "satisfied": case.satisfied,
            "source": case.source,
        }
        for case in harness.golden_cases()
        if case.procedure == procedure_id
    ]


def as_lang(value: str) -> Lang:
    """Narrow a request string to a supported language, or fall back to English.

    A form can only offer what `languages_for` listed, so anything else is a
    hand-made request rather than a click.
    """
    return cast(Lang, value) if value in get_args(Lang) else "en"


def languages_for(procedure_id: str) -> list[str]:
    """Installed languages this procedure declares, in the order the row declares them.

    The catalogue lists English first for every implemented row, and that is the
    sensible default; sorting alphabetically would open every form on German.
    """
    installed = set(installed_languages())
    declared = [lang for lang in get(procedure_id).meta.languages if lang in installed]
    return [str(lang) for lang in declared] or ["en"]


def can_apply(procedure_id: str) -> bool:
    return isinstance(get(procedure_id), Constructive)


#: Apply-only parameters the bench deliberately does not offer.
#:
#: `max_results` bounds `produce`, and `apply` is `produce(...).texts[0]`
#: (ADR 0026) — so every value above zero gives the bench the same single text.
#: A control that cannot change what the page shows is worse than a missing one:
#: it invites the reader to conclude the parameter does nothing.
UNOFFERED_APPLY_FIELDS = frozenset({"max_results"})


def apply_fields_for(procedure_id: str) -> list[Field]:
    """The parameters `apply` takes that `check` does not.

    The bench renders one form and posts it to either route, so before this
    existed the apply route coerced a posted value against the *checker's*
    schema and silently dropped everything the checker had never heard of.
    `seed` was the casualty that mattered: the ten procedures that draw
    (ADR 0025) took it as a form field, found no `seed` among the checker's
    fields, and drew unseeded — so the bench could not reproduce its own
    output, and `cut_up` on a three-word source returned its input often
    enough to fail its own identity guard about one run in three.

    `source` is excluded because `parse_apply_params` refuses a second one: the
    text being transformed is the source, and posting both names two.
    """
    # `ConstructiveProcedure` and not the `Constructive` protocol, which names
    # `apply` and `produce` — what a caller *does* — and not the parameter model
    # behind them. Widening the protocol to reach one dev tool's form builder is
    # the wrong direction; this asks the concrete base class that actually
    # declares `apply_params_model`, and every generator inherits it.
    procedure = get(procedure_id)
    if not isinstance(procedure, ConstructiveProcedure):
        return []
    already = {f.name for f in fields_for(procedure_id)} | {"source"} | UNOFFERED_APPLY_FIELDS
    schema = procedure.apply_params_model().model_json_schema()
    return [f for f in _fields_from(schema) if f.name not in already]


def wants_corpus(procedure_id: str) -> bool:
    """Whether this procedure draws from a corpus rather than a plain source.

    Asked of the procedure rather than hard-coded to `ideenwuerfeln`, so a
    second corpus-drawing procedure gets the picker without a change here.
    """
    return "corpus" in get(procedure_id).meta.requires or procedure_id == "ideenwuerfeln"


def pack_for(lang: str) -> LanguagePack:
    return get_pack(lang)


def run(
    procedure_id: str, text: str, lang: str, params: dict[str, Any]
) -> tuple[Report | None, str]:
    """Check a text, returning either a report or a message worth reading."""
    try:
        return get(procedure_id).check(text, lang=as_lang(lang), **params), ""
    except DenckringError as exc:
        return None, str(exc)


def generate(procedure_id: str, text: str, lang: str, params: dict[str, Any]) -> tuple[str, str]:
    """Produce text with a constructive procedure."""
    procedure = get(procedure_id)
    if not isinstance(procedure, Constructive):
        return "", f"{procedure_id} validates but does not generate."
    # Forwarded only when asked for: `seed` belongs to the procedures that draw,
    # and the unset `None` would be an unknown parameter to the ones that do not.
    seed = params.pop("seed", None)
    drawn = {"seed": seed} if seed is not None else {}
    params.pop("source", None)
    try:
        return procedure.apply(text, lang=as_lang(lang), **drawn, **params), ""
    except DenckringError as exc:
        return "", str(exc)
