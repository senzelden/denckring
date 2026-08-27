"""denckring — a library of experimental writing procedures."""

from importlib.metadata import version
from typing import Any

from denckring.core.describe import Description, Scholarly, Summary, describe, summaries
from denckring.core.errors import NotConstructive
from denckring.core.protocol import Constructive, Lang, Meta, Production, Report, Violation
from denckring.core.registry import all_procedures, get

__version__ = version("denckring")


def check(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> Report:
    """Check a text against a procedure by id."""
    return get(procedure_id).check(text, lang=lang, **params)


def apply(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> str:
    """Generate one text with a procedure by id — the best result it found."""
    return _constructive(procedure_id).apply(text, lang=lang, **params)


def produce(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> Production:
    """Generate with a procedure by id, returning every result it found."""
    return _constructive(procedure_id).produce(text, lang=lang, **params)


def _constructive(procedure_id: str) -> Constructive:
    """The procedure, or `NotConstructive` if it only checks.

    Raised rather than returned as a value, so a caller catches one kind of
    failure for one kind of mistake — `UnknownProcedure` and this are both
    `DenckringError`.
    """
    procedure = get(procedure_id)
    if not isinstance(procedure, Constructive):
        raise NotConstructive(procedure_id)
    return procedure


def list_procedures() -> list[str]:
    """Every registered procedure id, sorted."""
    return sorted(all_procedures())


__all__ = [
    "Description",
    "Lang",
    "Meta",
    "Production",
    "Report",
    "Scholarly",
    "Summary",
    "Violation",
    "__version__",
    "all_procedures",
    "apply",
    "check",
    "describe",
    "get",
    "list_procedures",
    "produce",
    "summaries",
]
