"""The catalogue as a machine reads it.

Four callers need this assembly — the CLI's `show`, the explorer, the MCP
server and the skill — so it lives here rather than in any one of them.
Computing it four times is how four copies drift apart.
"""

from __future__ import annotations

from typing import Any, get_args

from pydantic import BaseModel

from denckring.core import catalogue
from denckring.core.base import ConstructiveProcedure
from denckring.core.protocol import Constructive, Lang, LanguagePack, Meta
from denckring.core.registry import all_procedures, get


class Scholarly(BaseModel):
    """Where a procedure comes from. Returned only when asked for."""

    source: str
    attribution: str
    attested: str
    aliases: list[str]
    notes: str | None


class Summary(BaseModel):
    """One catalogue row, compact enough to list eighty of."""

    id: str
    name: str
    definition: str
    family: str
    kind: str
    runnable: bool
    constructive: bool


class Description(BaseModel):
    """Everything a model needs to use one procedure."""

    id: str
    name: str
    definition: str
    prompt_hints: str | None
    family: str
    kind: str
    #: Whether *this install* has a generator. Distinct from `kind`, which says
    #: whether the form admits one at all: nine rows are honestly `both` and
    #: honestly have no `apply` here, and a single field could not say both.
    constructive: bool
    checkability: str
    languages: list[str]
    #: Which languages this install can actually check the row in, computed from
    #: the packs' capabilities. `languages` above is authored editorial scope —
    #: `wechselsatz` is German by nature and not merely by capability — and the
    #: two answer different questions. Derived rather than authored so it cannot
    #: drift into the false claim a `[en]` row made once French began working.
    runs_in: list[str]
    requires: list[str]
    runnable: bool
    missing: list[str]
    apply_requires: list[str]
    apply_missing: list[str]
    params: dict[str, Any]
    #: JSON Schema for the parameters `apply` accepts, empty for a row with no
    #: generator to pass any to. Distinct from `params`, which is the checker's
    #: model and does not carry `seed` or `allow_identity` — so a caller that
    #: never touches Python could see neither, and the developer feedback that
    #: started this chapter was largely that the MCP surface does not say
    #: things. `params` is not merely a subset of this one: `source` is supplied
    #: by `apply` from the text it transforms, and passing it as a parameter is
    #: refused.
    apply_params: dict[str, Any]
    #: Which of `name`, `definition` and `prompt_hints` are not in the language
    #: asked for but in a substitute. Localisation has always fallen back to
    #: English, silently and per field, so a French caller received English prose
    #: in a field typed as French with nothing marking it: measured over 155 rows
    #: on 2026-09-04, `names` de 95 / fr 98, `definitions` de 95 / fr 95, and
    #: `prompt_hints` de 4 / fr 0. Empty means everything present is in `lang`.
    #: The fallback itself is unchanged — a substitute beats a blank field — this
    #: only stops it being invisible.
    untranslated: list[str]
    scholarly: Scholarly | None = None


def runnable(meta: Meta, lang: Lang = "en") -> tuple[bool, list[str]]:
    """Whether this install can run the procedure, and what it lacks.

    Returns rather than raises, because the caller is deciding what to offer
    rather than executing anything.
    """
    from denckring.lang import get_pack

    try:
        pack = get_pack(lang)
    except Exception:
        return False, list(meta.requires)
    missing = [cap for cap in meta.requires if cap not in pack.capabilities]
    return not missing, missing


def apply_runnable(
    meta: Meta, lang: Lang = "en", *, pack: LanguagePack | None = None
) -> tuple[bool, list[str]]:
    """Whether this install can *generate* with the procedure, and what it lacks.

    Separate from `runnable` because the two halves have different costs: a
    core-only install checks an anagram perfectly well and cannot generate one.
    Takes an optional pack so a test can ask about an install it is not running.
    """
    if pack is None:
        from denckring.lang import get_pack

        try:
            pack = get_pack(lang)
        except Exception:
            return False, [*meta.requires, *meta.apply_requires]
    missing = [
        capability
        for capability in (*meta.requires, *meta.apply_requires)
        if capability not in pack.capabilities
    ]
    return not missing, missing


def _text(mapping: dict[Lang, str], lang: Lang) -> str:
    """The requested language, falling back to English, then to anything."""
    if lang in mapping:
        return mapping[lang]
    if "en" in mapping:
        return mapping["en"]
    return next(iter(mapping.values()), "")


def _fell_back(mapping: dict[Lang, str], lang: Lang) -> bool:
    """Whether `_text` substituted another language for `lang`.

    An *empty* mapping is not a fallback: a row carrying no `prompt_hints` at all
    has none to translate, and `prompt_hints` is already `None` to say so.
    Reporting it as untranslated would say a row was mistranslated when it is
    merely silent, which is the error this field exists to avoid making.

    No catalogue row reaches that branch today — all 155 carry at least one
    `prompt_hints` entry, measured 2026-09-04 — but `prompt_hints` is optional in
    `Meta`, so the case is reachable by the next row added and is covered by a
    test against the mapping rather than against a row.
    """
    return bool(mapping) and lang not in mapping


def describe(procedure_id: str, *, lang: Lang = "en", scholarly: bool = False) -> Description:
    """One procedure, in full. Raises `UnknownProcedure` for an unknown id."""
    meta = catalogue.get(procedure_id)
    procedure = get(procedure_id)
    is_constructive = isinstance(procedure, Constructive)
    ok, missing = runnable(meta, lang)
    _, apply_missing = apply_runnable(meta, lang)
    return Description(
        id=meta.id,
        name=_text(meta.names, lang),
        definition=_text(meta.definitions, lang),
        prompt_hints=_text(meta.prompt_hints, lang) or None,
        family=meta.family,
        kind=meta.kind,
        constructive=is_constructive,
        checkability=meta.checkability,
        languages=list(meta.languages),
        runs_in=[lang for lang in get_args(Lang) if runnable(meta, lang)[0]],
        requires=list(meta.requires),
        runnable=ok,
        missing=missing,
        apply_requires=list(meta.apply_requires),
        apply_missing=apply_missing,
        untranslated=[
            field
            for field, mapping in (
                ("name", meta.names),
                ("definition", meta.definitions),
                ("prompt_hints", meta.prompt_hints),
            )
            if _fell_back(mapping, lang)
        ],
        params=procedure.params_model().model_json_schema(),
        # Asked of the spine rather than the `Constructive` protocol, which
        # declares `apply` alone. The two cannot disagree: every procedure that
        # defines `apply` inherits `ConstructiveProcedure`, which
        # `test_apply_spine.py::test_every_generator_is_on_the_spine` pins.
        apply_params=(
            procedure.apply_params_model().model_json_schema()
            if isinstance(procedure, ConstructiveProcedure)
            else {}
        ),
        scholarly=(
            Scholarly(
                source=meta.source,
                attribution=meta.attribution,
                attested=meta.attested,
                aliases=list(meta.aliases),
                notes=meta.notes,
            )
            if scholarly
            else None
        ),
    )


def _matches(meta: Meta, needle: str) -> bool:
    haystack = [meta.id, *meta.names.values(), *meta.aliases]
    return any(needle in field.casefold() for field in haystack)


def summaries(
    *,
    query: str | None = None,
    family: str | None = None,
    runnable_only: bool = False,
    lang: Lang = "en",
) -> list[Summary]:
    """The implemented procedures, filtered. `query` subsumes search.

    Only implemented rows appear: the other 66 catalogued forms have no checker,
    so offering them would be offering something that cannot run.
    """
    needle = query.casefold() if query else None
    rows: list[Summary] = []
    for procedure_id in all_procedures():
        meta = catalogue.get(procedure_id)
        if needle and not _matches(meta, needle):
            continue
        if family and meta.family != family:
            continue
        ok, _ = runnable(meta, lang)
        if runnable_only and not ok:
            continue
        rows.append(
            Summary(
                id=meta.id,
                name=_text(meta.names, lang),
                definition=_text(meta.definitions, lang),
                family=meta.family,
                kind=meta.kind,
                runnable=ok,
                constructive=isinstance(get(procedure_id), Constructive),
            )
        )
    return rows
