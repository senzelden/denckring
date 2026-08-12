"""Reading the catalogue the way the explorer wants it.

Everything here is derived from the library at request time. Nothing is copied,
so the explorer cannot fall out of step with the package it browses.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from denckring.core import catalogue
from denckring.core.protocol import FAMILIES, Meta
from denckring.core.registry import all_procedures
from denckring.eval import harness
from denckring.lang import get_pack, installed_languages

#: A sort is set (implemented), still to cut (catalogued), or blocked off
#: (never checkable). The type-case grid reads these three states.
SET = "set"
UNCUT = "uncut"
BLOCKED = "blocked"


@dataclass(frozen=True)
class Sort:
    """One procedure as it appears in the case."""

    id: str
    name: str
    family: str
    state: str
    checkability: str
    missing: tuple[str, ...]

    @property
    def initial(self) -> str:
        return self.name[0].upper()

    @property
    def blocked_on(self) -> str:
        return ", ".join(self.missing)


def _capabilities() -> set[str]:
    seen: set[str] = set()
    for lang in installed_languages():
        seen |= set(get_pack(lang).capabilities)
    return seen


def state_of(meta: Meta, implemented: set[str]) -> str:
    if meta.id in implemented:
        return SET
    if meta.checkability == "none":
        return BLOCKED
    return UNCUT


def sort_for(meta: Meta, implemented: set[str], available: set[str]) -> Sort:
    return Sort(
        id=meta.id,
        name=meta.names.get("en", meta.id),
        family=meta.family,
        state=state_of(meta, implemented),
        checkability=meta.checkability,
        missing=tuple(sorted(set(meta.requires) - available)),
    )


def case() -> list[tuple[str, list[Sort]]]:
    """The whole catalogue, laid out in drawers by family."""
    implemented = set(all_procedures())
    available = _capabilities()
    drawers: list[tuple[str, list[Sort]]] = []
    for family in FAMILIES:
        sorts = [
            sort_for(meta, implemented, available)
            for meta in catalogue.load().values()
            if meta.family == family
        ]
        if sorts:
            drawers.append((family, sorted(sorts, key=lambda s: s.name.lower())))
    return drawers


def coverage() -> dict[str, Any]:
    status = harness.status()
    return {
        "catalogued": status.catalogued,
        "implementable": status.implementable,
        "implemented": status.implemented,
        "validated": status.validated,
        "unreachable": status.unreachable,
        "remaining": status.implementable - status.implemented,
        "fraction": status.implemented / status.implementable if status.implementable else 0.0,
    }


def gaps() -> list[tuple[str, int, list[Sort]]]:
    """What is missing, grouped by the capability that blocks it.

    This is the view that answers "what is still to do" honestly: a row waiting
    on `lexicon.synonyms` is waiting on something nobody has written, and a row
    with no missing capability is simply unwritten.
    """
    implemented = set(all_procedures())
    available = _capabilities()
    grouped: dict[str, list[Sort]] = {}
    for meta in catalogue.load().values():
        if meta.id in implemented or meta.checkability == "none":
            continue
        sort = sort_for(meta, implemented, available)
        key = sort.blocked_on or "nothing — the checker is simply unwritten"
        grouped.setdefault(key, []).append(sort)
    ordered = (
        (key, len(rows), sorted(rows, key=lambda s: s.name.lower()))
        for key, rows in grouped.items()
    )
    return sorted(ordered, key=lambda item: (-item[1], item[0]))


def unreachable() -> list[Sort]:
    """The rows that can never have a checker, which are not a backlog."""
    implemented = set(all_procedures())
    available = _capabilities()
    return sorted(
        (
            sort_for(meta, implemented, available)
            for meta in catalogue.load().values()
            if meta.checkability == "none"
        ),
        key=lambda s: s.name.lower(),
    )


def family_counts() -> Counter[str]:
    return Counter(meta.family for meta in catalogue.load().values())


def find(term: str) -> list[Sort]:
    """Match an id, a name in any language, or an alias."""
    needle = term.casefold().strip()
    if not needle:
        return []
    implemented = set(all_procedures())
    available = _capabilities()
    found = []
    for meta in catalogue.load().values():
        haystack = [meta.id, *meta.names.values(), *meta.aliases]
        if any(needle in field.casefold() for field in haystack):
            found.append(sort_for(meta, implemented, available))
    return sorted(found, key=lambda s: s.name.lower())
