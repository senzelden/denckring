"""The catalogue is the single source of truth for procedure metadata."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import Layer, Meta

CATALOGUE_PATH = Path(str(files("denckring") / "data" / "catalogue.yaml"))


@lru_cache(maxsize=1)
def load() -> dict[str, Meta]:
    """Read every catalogue row. Cached: the file is read once per process."""
    raw: Any = yaml.safe_load(CATALOGUE_PATH.read_text(encoding="utf-8"))
    entries: dict[str, Meta] = {}
    for row in raw["procedures"]:
        meta = Meta.model_validate(row)
        if meta.id in entries:
            raise ValueError(f"Duplicate catalogue row for {meta.id!r}")
        entries[meta.id] = meta
    return entries


def get(procedure_id: str) -> Meta:
    """Return one entry, or raise `UnknownProcedure`."""
    try:
        return load()[procedure_id]
    except KeyError:
        raise UnknownProcedure(procedure_id) from None


def ids(layer: Layer | None = None) -> list[str]:
    """Every catalogued id, sorted; `layer` narrows to one of ADR 0033's two.

    Unnarrowed it stays what it was — both layers — because the catalogue is one
    dataset and `list`, `search` and `export` describe all of it. Only the coverage
    counters read one layer at a time.
    """
    return sorted(pid for pid, meta in load().items() if layer is None or meta.layer == layer)
