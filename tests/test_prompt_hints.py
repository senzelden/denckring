"""Prompt hints are templates, and every hint states the task it hints at (ADR 0050).

A caller that mints parameters — a lipogram forbidding `q` — builds its prompt from
the catalogue's hint. A hint written for the default parameters then asks for one
task while the checker judges another, and nothing notices: both halves look right
on their own. These tests assert the rule rather than any row's current wording, so
a hint rewritten for a good reason stays green as long as it still states its
parameters.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from denckring import check, describe, prompt_hint
from denckring.core import catalogue
from denckring.core.errors import InvalidParams, NoPromptHint, UnsetHintParameter
from denckring.core.hints import (
    UNSTATED_PARAMS,
    default_values,
    placeholders,
    rendered_with_defaults,
)
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures
from denckring.core.text import _CLAUSE_BREAK
from denckring.eval.harness import golden_cases

PROCEDURES = all_procedures()
ROWS = catalogue.load()
HINTS = [(pid, lang) for pid, meta in sorted(ROWS.items()) for lang in meta.prompt_hints]
IMPLEMENTED_HINTS = [(pid, lang) for pid, lang in HINTS if pid in PROCEDURES]


#: Values for hint slots that default to `None` ("inferred") and that no golden
#: fixture of the row sets in that language. Adding the fixtures instead would change
#: `denckring eval --all`, which this change must leave as it found it, so the
#: gap is filled here — narrowly, one value per slot, and
#: `test_an_unfixtured_slot_is_one_no_fixture_of_its_row_sets` removes each entry's
#: licence the day a fixture supplies it. `prompt_hint` still validates each one
#: through the row's own params model.
UNFIXTURED_SLOTS: dict[tuple[str, Lang], dict[str, Any]] = {
    ("ideenwuerfeln", "en"): {"headword": "Zeit"},
    ("llull_figure", "en"): {"level": "absolute"},
    ("renga", "en"): {"links": 3},
    ("reverse_snowball", "en"): {"start": 6},
    ("serial_lipogram", "en"): {"start": "a"},
    ("snowball", "en"): {"start": 1},
    ("snowball_sentence", "en"): {"start": 1},
}


#: How an English hint names each mark `clause_spans` splits on.
#: `clause_spans` also cuts at every line break, through `line_spans`.
CLAUSE_MARK_NAMES: dict[str, str] = {
    ",": "comma",
    ";": "semicolon",
    ":": "colon",
    "\n": "line break",
}


def _properties(pid: str) -> dict[str, Any]:
    if pid not in PROCEDURES:
        return {}
    properties: dict[str, Any] = PROCEDURES[pid].params_schema().get("properties", {})
    return properties


@pytest.mark.parametrize(("pid", "lang"), HINTS, ids=[f"{p}:{lang}" for p, lang in HINTS])
def test_every_placeholder_names_a_parameter_of_its_row(pid: str, lang: Lang) -> None:
    """A placeholder naming no parameter can never be filled.

    Covers the catalogue rows with no registered procedure too: they have no
    parameters, so any placeholder in their hints is a defect.
    """
    named = placeholders(ROWS[pid].prompt_hints[lang])
    unknown = sorted(set(named) - set(_properties(pid)))
    assert not unknown, f"{pid}:{lang} hint names {unknown}, which are not parameters"


@pytest.mark.parametrize(
    ("pid", "lang"), IMPLEMENTED_HINTS, ids=[f"{p}:{lang}" for p, lang in IMPLEMENTED_HINTS]
)
def test_every_hint_renders(pid: str, lang: Lang) -> None:
    """With the defaults where they fill every slot, else with each fixture's params.

    A hint naming a parameter with no default, or one defaulting to `None`,
    cannot render from defaults alone. Its golden fixtures carry values the
    checker already accepts, so every fixture in this language that supplies each
    such slot must render. Where none does, every fixture renders with the gap
    filled from `UNFIXTURED_SLOTS`. A row with no fixture in the language, or a
    gap nothing fills, is a failure, not a skip: a hint nobody has rendered is a
    hint nobody knows reads correctly.
    """
    procedure = PROCEDURES[pid]
    template = ROWS[pid].prompt_hints[lang]
    unfilled = set(placeholders(template)) - set(default_values(procedure.params_model()))
    if not unfilled:
        rendered = rendered_with_defaults(pid, template, procedure.params_model())
        assert "{" not in rendered and "}" not in rendered, rendered
        if not procedure.params_schema().get("required"):
            assert prompt_hint(pid, lang=lang) == rendered
        return
    cases = [case for case in golden_cases() if case.procedure == pid and case.lang == lang]
    assert cases, f"{pid}:{lang} needs {sorted(unfilled)} and has no golden fixture to render with"
    renderings = [case.params for case in cases if unfilled <= set(case.params)] or [
        {**UNFIXTURED_SLOTS.get((pid, lang), {}), **case.params} for case in cases
    ]
    for params in renderings:
        missing = sorted(unfilled - set(params))
        assert not missing, f"{pid}:{lang}: no fixture or UNFIXTURED_SLOTS entry gives {missing}"
        rendered = prompt_hint(pid, lang=lang, **params)
        assert "{" not in rendered and "}" not in rendered, rendered


def test_an_unfixtured_slot_is_one_no_fixture_of_its_row_sets() -> None:
    """`UNFIXTURED_SLOTS` fills gaps and may not shadow a fixture's own value.

    Once a fixture sets the parameter, its entry here is stale: delete it, so the
    render uses a value the checker has judged rather than one written for this
    test.
    """
    for (pid, lang), slots in UNFIXTURED_SLOTS.items():
        assert lang in ROWS[pid].prompt_hints, f"{pid}:{lang} has no hint to fill"
        for name in slots:
            setting = [
                case.name
                for case in golden_cases()
                if case.procedure == pid and case.lang == lang and name in case.params
            ]
            assert not setting, f"{pid}:{lang}.{name} is set by {setting}; drop the example"


@pytest.mark.parametrize(
    ("pid", "lang"), IMPLEMENTED_HINTS, ids=[f"{p}:{lang}" for p, lang in IMPLEMENTED_HINTS]
)
def test_every_task_parameter_is_stated_or_declared_unstated(pid: str, lang: Lang) -> None:
    """The rule the feature exists for: a hint cannot quietly keep a default.

    A parameter may stay out of a hint only for a recorded reason — house-wide in
    `UNSTATED_PARAMS`, or for this row in its catalogue `hint_omits`.
    """
    stated = set(placeholders(ROWS[pid].prompt_hints[lang]))
    exempt = set(UNSTATED_PARAMS) | set(ROWS[pid].hint_omits)
    silent = sorted(set(_properties(pid)) - stated - exempt)
    assert not silent, (
        f"{pid}:{lang} hint neither states {silent} as a placeholder nor declares it in hint_omits"
    )


@pytest.mark.parametrize("pid", sorted(ROWS), ids=sorted(ROWS))
def test_a_declared_omission_is_a_real_parameter_left_unstated_for_a_reason(pid: str) -> None:
    """An omission naming nothing, or naming what the hint states, is stale."""
    meta = ROWS[pid]
    for name, reason in meta.hint_omits.items():
        assert name in _properties(pid), f"{pid}: hint_omits names {name!r}, not a parameter"
        assert name not in UNSTATED_PARAMS, f"{pid}: {name!r} is already exempt house-wide"
        assert reason.strip(), f"{pid}: hint_omits gives {name!r} no reason"
        for lang, hint in meta.prompt_hints.items():
            assert name not in placeholders(hint), f"{pid}:{lang} states omitted {name!r}"


def test_house_wide_exemptions_each_carry_a_reason() -> None:
    assert all(reason.strip() for reason in UNSTATED_PARAMS.values())


def test_a_minted_parameter_reaches_the_prompt() -> None:
    """The case the renderer exists for: a value other than the default."""
    assert '"q"' in prompt_hint("lipogram", forbidden="q")
    assert '"q"' not in prompt_hint("lipogram")


def test_parameters_are_validated_as_check_validates_them() -> None:
    """Defaults fill in, and a bad value refuses in the same words `check` uses."""
    with pytest.raises(InvalidParams):
        prompt_hint("lipogram", forbidden="qq")
    with pytest.raises(InvalidParams):
        prompt_hint("lipogram", forbiden="q")


def test_a_value_the_validator_normalises_is_rendered_normalised() -> None:
    """The prompt states what the checker will judge, not what the caller typed."""
    assert '"a"' in prompt_hint("abecedarian", start="A")


def test_a_list_renders_as_its_items_joined_by_comma_and_space() -> None:
    """The one rule for non-string values: sequences join, everything else is `str`."""
    assert "5, 7, 5" in prompt_hint("syllable_count", pattern=[5, 7, 5])
    # A non-default integer, so the assertion can tell a rendered value from the
    # default the template would otherwise print.
    rendered = prompt_hint("every_nth_word", source="a b c", n=3)
    assert "every 3 " in rendered and "every 7 " not in rendered


def test_a_placeholder_left_unset_is_refused_by_name() -> None:
    """`None` means "inferred" to a checker and means nothing in a sentence."""
    with pytest.raises(UnsetHintParameter) as raised:
        prompt_hint("tautogram")
    assert "initial" in str(raised.value)
    assert raised.value.detail()["param"] == "initial"


def test_a_row_without_a_hint_in_the_language_is_refused() -> None:
    """No fallback: a prompt in the wrong language is not a prompt in this one.

    `describe` falls back to English and says so in `untranslated`; a renderer
    returning a string has no such channel, so it refuses instead.
    """
    pid, lang = next(
        (pid, lang)
        for pid, meta in sorted(ROWS.items())
        if pid in PROCEDURES
        for lang in ("en", "de", "fr")
        if lang not in meta.prompt_hints and not _properties(pid)
    )
    with pytest.raises(NoPromptHint) as raised:
        prompt_hint(pid, lang=lang)  # type: ignore[arg-type]
    assert raised.value.detail() == {"procedure_id": pid, "lang": lang}


def test_describe_renders_defaults_where_every_placeholder_has_one() -> None:
    """So `describe`, the CLI and MCP keep showing a hint a model can act on."""
    hint = describe("lipogram").prompt_hints
    assert hint is not None and "{" not in hint and '"e"' in hint


def test_describe_keeps_the_template_where_a_placeholder_has_no_default() -> None:
    """Its `params` schema, beside it, names what the slot wants."""
    template = ROWS["acrostic"].prompt_hints["en"]
    assert "{target}" in template
    assert describe("acrostic").prompt_hints == template


#: Two constraints, each with a non-default parameter, so a sub-hint rendered from
#: its defaults or left out entirely cannot pass.
COMPOSITE: dict[str, Any] = {
    "constraints": ["lipogram", "univocalic"],
    "constraint_params": {"lipogram": {"forbidden": "q"}, "univocalic": {"vowel": "o"}},
}


def test_a_composite_hint_states_each_constraint_with_its_own_params() -> None:
    """`constraint_params` changes the task, so the prompt has to say it.

    The composite's own hint comes first, then one `- ` line per named
    constraint, in `constraints` order, each rendered by the same renderer.
    """
    lines = prompt_hint("multiple_constraint", **COMPOSITE).split("\n")
    assert lines[1:] == [
        "- " + prompt_hint("lipogram", forbidden="q"),
        "- " + prompt_hint("univocalic", vowel="o"),
    ]
    assert '"q"' in lines[1] and '"o"' in lines[2]


def test_a_sub_constraint_is_validated_as_its_own_check_would() -> None:
    bad = {**COMPOSITE, "constraint_params": {"lipogram": {"forbidden": "qq"}}}
    with pytest.raises(InvalidParams) as raised:
        prompt_hint("multiple_constraint", **bad)
    assert raised.value.procedure_id == "lipogram"


def test_a_sub_constraint_left_unset_is_refused_by_name() -> None:
    unset = {**COMPOSITE, "constraint_params": {"lipogram": {"forbidden": "q"}}}
    with pytest.raises(UnsetHintParameter) as raised:
        prompt_hint("multiple_constraint", **unset)
    assert raised.value.detail() == {"procedure_id": "univocalic", "param": "vowel"}


def test_a_sub_constraint_without_a_hint_in_the_language_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No catalogue row reaches this today: every row has an English hint and the
    composite has only English, so the composite would refuse first. A German
    composite hint is patched in to reach the sub-constraint's own refusal."""
    monkeypatch.setitem(
        ROWS["multiple_constraint"].prompt_hints, "de", "Erfülle zugleich: {constraints}."
    )
    with pytest.raises(NoPromptHint) as raised:
        prompt_hint("multiple_constraint", lang="de", **COMPOSITE)
    assert raised.value.detail() == {"procedure_id": "lipogram", "lang": "de"}


def _clause_unit_hints() -> list[str]:
    return [
        pid
        for pid, lang in IMPLEMENTED_HINTS
        if lang == "en" and "clause" in _properties(pid).get("unit", {}).get("enum", [])
    ]


def test_every_clause_break_mark_has_an_english_name() -> None:
    assert set(_CLAUSE_BREAK) <= set(CLAUSE_MARK_NAMES), "name the new mark for the hints"


@pytest.mark.parametrize("pid", _clause_unit_hints())
def test_a_clause_unit_hint_names_every_mark_that_ends_a_clause(pid: str) -> None:
    """A clause is whatever `clause_spans` cuts at, not a grammatical clause.

    A writer who ends a clause with the closing word and then puts a comma inside the
    next one ("the old mill, moving, while ...") has, for the checker, a clause ending
    in "mill". The hint is the only place a writer can learn where the cuts fall.
    """
    hint = ROWS[pid].prompt_hints["en"]
    marks = [*_CLAUSE_BREAK, "\n"]
    unnamed = [mark for mark in marks if CLAUSE_MARK_NAMES[mark] not in hint]
    assert not unnamed, f"{pid}: the hint never says a clause ends at {unnamed}"


#: A quoted literal, in straight or curly double quotes. One holding a placeholder
#: quotes the caller's value ("{forbidden}"), not an example, and is skipped.
QUOTED = re.compile(r"\"([^\"]*)\"|\u201c([^\u201d]*)\u201d")
#: The phrase an example marker introduces, up to the next clause punctuation.
EXAMPLE_PHRASE = re.compile(r"\b(?:such as|as in|e\.g\.)\s+([^;:.()]+?)(?=[,;:.()]|$)")


def hint_examples(hint: str) -> list[str]:
    """Every example a hint offers: its quoted literals and the items after "such as"."""
    found = [
        literal
        for match in QUOTED.finditer(hint)
        if (literal := match.group(1) or match.group(2) or "") and "{" not in literal
    ]
    for match in EXAMPLE_PHRASE.finditer(hint):
        phrase = match.group(1)
        if '"' not in phrase and "\u201c" not in phrase:
            found += [item.strip() for item in re.split(r",| or | and ", phrase) if item.strip()]
    return found


def _judged_params(pid: str, lang: Lang) -> list[dict[str, Any]]:
    """The params `test_every_hint_renders` renders with: defaults, else each fixture's."""
    procedure = PROCEDURES[pid]
    template = ROWS[pid].prompt_hints[lang]
    unfilled = set(placeholders(template)) - set(default_values(procedure.params_model()))
    if not unfilled and not procedure.params_schema().get("required"):
        return [{}]
    cases = [case for case in golden_cases() if case.procedure == pid and case.lang == lang]
    return [dict(case.params) for case in cases if unfilled <= set(case.params)] or [
        {**UNFIXTURED_SLOTS.get((pid, lang), {}), **case.params} for case in cases
    ]


def test_hint_examples_finds_quoted_literals_and_listed_examples() -> None:
    hint = 'Omit "{forbidden}" and write "abso-bloody-lutely", such as tartar or couscous.'
    assert hint_examples(hint) == ["abso-bloody-lutely", "tartar", "couscous"]


EXAMPLE_HINTS = [(pid, lang) for pid, lang in IMPLEMENTED_HINTS if lang == "en"]


@pytest.mark.parametrize("pid", [pid for pid, _ in EXAMPLE_HINTS])
def test_no_example_in_a_hint_is_itself_a_passing_answer(pid: str) -> None:
    """A hint states the task; it never hands over an answer.

    The prompt a benchmark sends is the hint and nothing else, so an example that
    satisfies the checker on its own turns the row into a copying test: "such as
    couscous" in the tautonym hint made "couscous" a perfect score.
    """
    for example in hint_examples(ROWS[pid].prompt_hints["en"]):
        for params in _judged_params(pid, "en"):
            report = check(pid, example, lang="en", **params)
            assert not report.satisfied, f"{pid}: the hint's example {example!r} passes {params}"
