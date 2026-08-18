"""denckring — a library of experimental writing procedures."""

from importlib.metadata import version
from typing import Any

from denckring.core.describe import Description, Scholarly, Summary, describe, summaries
from denckring.core.protocol import Lang, Meta, Report, Violation
from denckring.core.registry import all_procedures, get

__version__ = version("denckring")


def check(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> Report:
    """Check a text against a procedure by id."""
    return get(procedure_id).check(text, lang=lang, **params)


def list_procedures() -> list[str]:
    """Every registered procedure id, sorted."""
    return sorted(all_procedures())


__all__ = [
    "Description",
    "Lang",
    "Meta",
    "Report",
    "Scholarly",
    "Summary",
    "Violation",
    "__version__",
    "all_procedures",
    "check",
    "describe",
    "get",
    "list_procedures",
    "summaries",
]
