"""denckring — a library of experimental writing procedures."""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from denckring.core.describe import Description, Scholarly, Summary, describe, summaries
from denckring.core.errors import (
    DegenerateOutput,
    DenckringError,
    DuplicatePack,
    DuplicateProcedure,
    InputTooLong,
    InputTooShort,
    InvalidParams,
    MalformedCorpus,
    MalformedDevice,
    MalformedFigure,
    MalformedTable,
    MissingCapability,
    NoCandidateWord,
    NoPromptHint,
    NotConstructive,
    TextTooLong,
    UnknownDevice,
    UnknownFigure,
    UnknownLanguage,
    UnknownLevel,
    UnknownProcedure,
    UnsetHintParameter,
    UnsettablePhrase,
)
from denckring.core.hints import placeholders, render, show_kinds
from denckring.core.protocol import (
    Constructive,
    Evidence,
    Lang,
    LanguagePack,
    Meta,
    PosTag,
    Production,
    Report,
    Violation,
)
from denckring.core.registry import all_procedures, get
from denckring.eval.harness import GoldenCase
from denckring.lang import get_pack

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
    lines = [render(procedure_id, template, dict(parsed), show_kinds(procedure.params_model()))]
    lines += [
        f"- {prompt_hint(delegate, lang=lang, **delegate_params)}"
        for delegate, delegate_params in procedure.hint_delegates(parsed)
    ]
    return "\n".join(lines)


def render_hint(procedure_id: str, template: str, *, lang: Lang = "en", **params: Any) -> str:
    """Render a template the caller owns by the rule `prompt_hint` uses.

    For a caller writing its own prompt for a row rather than using the catalogue's.
    `params` are validated as `check` validates them, so defaults fill in and a bad
    value raises `InvalidParams`; `lang` must name a language a pack is installed
    for, as it must for `check`. Values render as in `prompt_hint`: a list joins with
    ", ", a field declaring `x-denckring-show: letters` quotes each letter (`"e",
    "t"`), anything else is `str()`. A placeholder naming no parameter of the row
    raises `InvalidParams`; one whose value is `None` raises `UnsetHintParameter`.
    Unlike `prompt_hint`, nothing is appended for a composite's constraints: the
    template is the whole prompt.
    """
    procedure = get(procedure_id)
    get_pack(lang)
    model = procedure.params_model()
    unknown = sorted(set(placeholders(template)) - set(model.model_fields))
    if unknown:
        raise InvalidParams(
            procedure_id,
            f"template names {unknown}, which are not parameters of this row; "
            f"it accepts {sorted(model.model_fields)}",
        )
    parsed = procedure.parse_params(params)
    return render(procedure_id, template, dict(parsed), show_kinds(model))


def rules(procedure_id: str) -> tuple[str, ...]:
    """Every `violation.rule` the row's checker can emit, sorted.

    The vocabulary each row declares (`BaseProcedure.rules`), so a caller can map
    rules to its own classes without reading checker source. `multiple_constraint`
    passes its constraints' violations through unchanged, and any registered row
    can be one of them, so it answers with every other row's vocabulary.

    Published from 0.3.2 but not yet under the README's stability promise: a rule
    may still be renamed in a minor release, and the changelog will say so.
    """
    procedure = get(procedure_id)
    if not procedure.delegates_rules:
        return procedure.rules
    return tuple(
        sorted(
            {
                rule
                for other in all_procedures().values()
                if not other.delegates_rules
                for rule in other.rules
            }
        )
    )


def golden_cases(lang: Lang | None = None, *, runnable: bool = True) -> list[GoldenCase]:
    """The shipped golden examples, each a text with the verdict its row must give.

    Every case names its row (`procedure`), its `lang`, the `text` and the `params`
    to check it with, and the recorded verdict (`satisfied`, with `min_score` or
    `max_score` where the score is pinned too). `provenance` says where the text
    came from: `external` (a published work), `constructed` (written for the suite)
    or `self-generated` (the row's own `apply`). Only `external` is evidence about
    the reading rather than the code. `requires` lists capabilities the case needs
    beyond its row's.

    `lang` keeps one language's cases. `runnable`, the default, keeps the cases this
    install can run: the language's pack declares every capability the row and the
    case require. A case it drops would end in `MissingCapability`, or would give an
    answer about the installed data rather than the text, which is why the scoreboard
    blocks it rather than scoring it. Pass `runnable=False` for the whole corpus.
    """
    from denckring.eval.harness import golden_cases as every_case
    from denckring.eval.harness import unmet_requirements

    cases = [case for case in every_case() if lang is None or case.lang == lang]
    if not runnable:
        return cases

    def runs(case: GoldenCase) -> bool:
        pack = get_pack(case.lang)
        needed = get(case.procedure).meta.requires
        return all(name in pack.capabilities for name in needed) and not unmet_requirements(
            case, pack
        )

    return [case for case in cases if runs(case)]


def list_procedures() -> list[str]:
    """Every registered procedure id, sorted."""
    return sorted(all_procedures())


__all__ = [
    "DegenerateOutput",
    "DenckringError",
    "Description",
    "DuplicatePack",
    "DuplicateProcedure",
    "Evidence",
    "GoldenCase",
    "InputTooLong",
    "InputTooShort",
    "InvalidParams",
    "Lang",
    "LanguagePack",
    "MalformedCorpus",
    "MalformedDevice",
    "MalformedFigure",
    "MalformedTable",
    "Meta",
    "MissingCapability",
    "NoCandidateWord",
    "NoPromptHint",
    "NotConstructive",
    "PosTag",
    "Production",
    "Report",
    "Scholarly",
    "Summary",
    "TextTooLong",
    "UnknownDevice",
    "UnknownFigure",
    "UnknownLanguage",
    "UnknownLevel",
    "UnknownProcedure",
    "UnsetHintParameter",
    "UnsettablePhrase",
    "Violation",
    "__version__",
    "all_procedures",
    "apply",
    "check",
    "describe",
    "get",
    "get_pack",
    "golden_cases",
    "list_procedures",
    "produce",
    "prompt_hint",
    "render_hint",
    "rules",
    "summaries",
]
