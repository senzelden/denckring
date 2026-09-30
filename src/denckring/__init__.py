"""denckring — a library of experimental writing procedures."""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from denckring.core.describe import Description, Scholarly, Summary, describe, summaries
from denckring.core.errors import NoPromptHint, NotConstructive
from denckring.core.hints import render
from denckring.core.protocol import Constructive, Lang, Meta, Production, Report, Violation
from denckring.core.registry import all_procedures, get

try:
    __version__ = version("denckring")
except PackageNotFoundError:
    #: A bare `PYTHONPATH=src` checkout has no installed distribution to read
    #: a version from. The documented uv workflow always installs first, so
    #: this is a fallback for ad-hoc source-tree tooling, not the normal path
    #: (review finding P3-02) — installed metadata stays authoritative.
    __version__ = "0+unknown"


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


def prompt_hint(procedure_id: str, *, lang: Lang = "en", **params: Any) -> str:
    """The row's prompt hint in `lang`, stating the parameters given (ADR 0050).

    `params` are validated as `check` validates them, so defaults fill in and a
    bad value raises `InvalidParams` exactly as it would there. Values render by
    one rule: a list or tuple joins its items with ", ", anything else is `str()`.

    Raises `NoPromptHint` when the row has no hint in `lang` — no fallback to
    English, which `describe` does and discloses in `untranslated`, but a bare
    string cannot — and `UnsetHintParameter` when the hint states a parameter
    whose value is `None` ("inferred" to a checker, nothing to a sentence).

    A composite (`multiple_constraint`) is followed by one line per named
    constraint, `- ` and that constraint's own hint rendered from its
    `constraint_params` entry by this same function, in `constraints` order. So
    each sub-hint validates and refuses as it would if asked for directly, and
    the error names the sub-constraint.
    """
    procedure = get(procedure_id)
    template = procedure.meta.prompt_hints.get(lang)
    if template is None:
        raise NoPromptHint(procedure_id, lang)
    parsed = procedure.parse_params(params)
    lines = [render(procedure_id, template, dict(parsed))]
    lines += [
        f"- {prompt_hint(delegate, lang=lang, **delegate_params)}"
        for delegate, delegate_params in procedure.hint_delegates(parsed)
    ]
    return "\n".join(lines)


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
    "prompt_hint",
    "summaries",
]
