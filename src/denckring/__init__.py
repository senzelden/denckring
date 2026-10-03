"""denckring — a library of experimental writing procedures."""

from collections.abc import Iterable
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
    NotWordLocal,
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
from denckring.core.provenance import PackProvenance
from denckring.core.provenance import pack_provenance as _describe_pack
from denckring.core.registry import all_procedures, get
from denckring.core.rules import CATEGORIES, RULE_CATEGORIES
from denckring.core.scope import SCOPES
from denckring.eval.harness import GoldenCase
from denckring.lang import get_pack
from denckring.lang.base import graded_view

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


def pack_provenance(lang: Lang = "en") -> PackProvenance:
    """Which pack answers for `lang` on this install, and which data it reads.

    The same record every `Report.provenance.pack` carries, without checking a text
    first: the pack's class, and each data distribution it reads mapped to its
    installed version (empty for a built-in default). A caller recording a run, or
    choosing what to draw from, reads it here rather than `getattr`ing the pack's
    `data_distributions`, which is not part of the `LanguagePack` protocol.
    """
    return _describe_pack(get_pack(lang), lang)


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
        return _declared(procedure)
    return tuple(
        sorted(
            {
                rule
                for other in all_procedures().values()
                if not other.delegates_rules
                for rule in _declared(other)
            }
        )
    )


def rule_categories(procedure_id: str) -> dict[str, str]:
    """Each rule `rules(procedure_id)` returns, mapped to the kind of failure it names.

    The categories are a closed set, defined in `failure_categories()`: a forbidden
    letter is `excluded_letter`, a missing line `count`, a broken rhyme `sound`. One
    category per rule string, the same on every row that emits it, so a caller
    counting failures across rows counts by kind without a map of its own (audit C3).
    Published with the rules themselves, and under the same terms: a rule's category
    may move in a minor release, and the changelog will say so.
    """
    return {rule: RULE_CATEGORIES[rule] for rule in rules(procedure_id)}


def failure_categories() -> dict[str, str]:
    """Every failure category `rule_categories` uses, mapped to what it means."""
    return dict(CATEGORIES)


def scope(procedure_id: str, **params: Any) -> str:
    """The smallest unit the row judges alone under these parameters (audit C2).

    One of `scopes()`: `word`, `line`, `sentence`, or `text` for no promise. A
    word-scoped row passes a text of words if and only if it passes each word
    alone, so a caller composing rows can build a passing text from passing
    words. The parameters matter: `tautogram` is word-scoped only with `initial`
    stated, since unset it reads the initial off the text's first word. Validated
    as `check` validates them.
    """
    procedure = get(procedure_id)
    return procedure.scope(procedure.parse_params(params))


def scopes() -> dict[str, str]:
    """Every scope `scope` returns, mapped to what it promises."""
    return dict(SCOPES)


def _word_local(procedure_id: str, params: dict[str, Any]) -> None:
    """Refuse a row that does not judge each word alone, naming what would make it."""
    procedure = get(procedure_id)
    parsed = procedure.parse_params(params)
    found = procedure.scope(parsed)
    if found != "word":
        raise NotWordLocal(procedure_id, found, procedure.unset_inferred(parsed))


def admits(procedure_id: str, word: str, /, *, lang: Lang = "en", **params: Any) -> bool:
    """Whether a word-scoped row passes `word` alone, and so in any text of such words.

    Raises `NotWordLocal` when `scope(procedure_id, **params)` is not `word`: a
    word alone has no verdict of its own there. Equal to
    `check(procedure_id, word, ...).satisfied`; the scope is what makes that
    answer hold in every text the word is joined into.
    """
    _word_local(procedure_id, params)
    return check(procedure_id, word, lang=lang, **params).satisfied


def witness(
    procedure_id: str,
    vocabulary: Iterable[str],
    /,
    *,
    lang: Lang = "en",
    size: int = 12,
    **params: Any,
) -> str:
    """A text the row passes, built from `vocabulary`: proof the parameters can be met.

    Golden cases prove a row satisfiable at its defaults; this proves it at any
    parameters a word-scoped row is given (audit C6). It joins, by spaces and in
    vocabulary order, the first `size` entries that are each one word as the
    pack splits them and that the row admits. Raises `NotWordLocal` as `admits`
    does, `InvalidParams` for a `size` under 1, and `NoCandidateWord` when no
    entry is admitted, which is the vocabulary's answer, not the row's.
    """
    if size < 1:
        raise InvalidParams(procedure_id, f"size must be at least 1, not {size}")
    _word_local(procedure_id, params)
    pack = get_pack(lang)
    chosen: list[str] = []
    for entry in vocabulary:
        if [word for _, word in pack.word_spans(entry)] != [entry]:
            continue
        if check(procedure_id, entry, lang=lang, **params).satisfied:
            chosen.append(entry)
            if len(chosen) == size:
                break
    if not chosen:
        raise NoCandidateWord(
            procedure_id,
            "no word of the vocabulary passes alone under these parameters — try a "
            "larger vocabulary or other parameters",
        )
    return " ".join(chosen)


def words(
    lang: Lang = "en", *, max_band: int | None = None, letters_only: bool = True
) -> tuple[str, ...]:
    """The language's graded words up to `max_band`, commonest band first (audit D1).

    The words a caller drawing everyday vocabulary wants: the pack's
    `graded_words()` kept to bands up to `max_band` (SCOWL's size classes in
    English, where 10 is the commonest), to words of letters alone when
    `letters_only`, and without the entries a pack excludes as no everyday word
    (`payed`, `numbest`; ADR 0051). Sorted by band, then alphabetically. No
    checker reads this view, so it moves no verdict. Raises `MissingCapability`
    when the pack grades no words.
    """
    return graded_view(get_pack(lang), max_band, letters_only=letters_only)


def nouns(lang: Lang = "en", *, max_band: int | None = None) -> tuple[str, ...]:
    """The nouns N+7 counts through, in its order, optionally only everyday ones (D5).

    With `max_band` unset, exactly the dictionary `n_plus_7` and `s_plus_7` read
    when no `dictionary` is passed, which a prompt asking for N+7 must print,
    since the answer is in it. With `max_band`, only the nouns that `words(lang,
    max_band=max_band, letters_only=False)` also lists, still in dictionary order,
    so a caller can build a source whose every noun a reader can be shown.
    """
    pack = get_pack(lang)
    dictionary = tuple(pack.nouns())
    if max_band is None:
        return dictionary
    everyday = set(graded_view(pack, max_band, letters_only=False))
    return tuple(noun for noun in dictionary if noun in everyday)


def _declared(procedure: Any) -> tuple[str, ...]:
    """A row's `rules`, or an error naming the row that forgot them.

    `BaseProcedure.rules` has no default by design, so a plugin or a new row without
    one would surface as a bare `AttributeError`, and through `multiple_constraint`'s
    union it would name the composite rather than the row at fault.
    """
    declared: tuple[str, ...] | None = getattr(procedure, "rules", None)
    if declared is None:
        raise TypeError(
            f"procedure {procedure.id!r} declares no `rules`; every row lists the "
            "`violation.rule` values its checker can emit (CONTRIBUTING.md)"
        )
    return declared


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
    "NotWordLocal",
    "PackProvenance",
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
    "admits",
    "all_procedures",
    "apply",
    "check",
    "describe",
    "failure_categories",
    "get",
    "get_pack",
    "golden_cases",
    "list_procedures",
    "nouns",
    "pack_provenance",
    "produce",
    "prompt_hint",
    "render_hint",
    "rule_categories",
    "rules",
    "scope",
    "scopes",
    "summaries",
    "witness",
    "words",
]
