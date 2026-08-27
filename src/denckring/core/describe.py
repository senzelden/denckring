"""The catalogue as a machine reads it.

Four callers need this assembly — the CLI's `show`, the explorer, the MCP
server and the skill — so it lives here rather than in any one of them.
Computing it four times is how four copies drift apart.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from denckring.core import catalogue
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
    requires: list[str]
    runnable: bool
    missing: list[str]
    apply_requires: list[str]
    apply_missing: list[str]
    params: dict[str, Any]
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
        requires=list(meta.requires),
        runnable=ok,
        missing=missing,
        apply_requires=list(meta.apply_requires),
        apply_missing=apply_missing,
        params=procedure.params_model().model_json_schema(),
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
