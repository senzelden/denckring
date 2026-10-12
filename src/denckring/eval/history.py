"""The shipped history of each row's checker (ADR 0061).

`checker-history.yaml` lists, per row and oldest first, every `checker_version` the row
has had and the release it shipped in. A caller comparing results across releases reads
it to learn whether a row's verdicts could have moved, which the package version cannot
say. `tests/test_checker_version.py` holds each list to the row's current version.
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files

import yaml
from pydantic import BaseModel, ConfigDict


class CheckerChange(BaseModel):
    """One entry of a row's checker history."""

    model_config = ConfigDict(frozen=True)

    version: int
    #: The release the change ships in.
    since: str
    reason: str


@cache
def _load() -> dict[str, tuple[CheckerChange, ...]]:
    text = (files("denckring") / "eval" / "checker-history.yaml").read_text(encoding="utf-8")
    raw = yaml.safe_load(text) or {}
    return {
        pid: tuple(CheckerChange.model_validate(entry) for entry in entries)
        for pid, entries in raw.items()
    }


def load() -> dict[str, list[CheckerChange]]:
    """Every row's history, keyed by id. A fresh copy, so a caller cannot edit the cache."""
    return {pid: list(changes) for pid, changes in _load().items()}
