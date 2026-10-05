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

from denckring import check, describe, prompt_hint, render_hint
from denckring.core import catalogue
from denckring.core.errors import InvalidParams, NoPromptHint, UnsetHintParameter
from denckring.core.fields import ROLES, roles
from denckring.core.hints import (
    STATED_ROLES,
    default_values,
    placeholders,
    rendered_with_defaults,
    unstated,
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

    A parameter may stay out of a hint only for a recorded reason: its role
    (`x-denckring-role`) is not one a hint states, or, for a task parameter, this
    row's catalogue `hint_omits` names it (audit C1).
    """
    procedure = PROCEDURES[pid]
    stated = set(placeholders(ROWS[pid].prompt_hints[lang]))
    exempt = set(unstated(procedure.params_model(), ROWS[pid].hint_omits))
    silent = sorted(set(_properties(pid)) - stated - exempt)
    assert not silent, (
        f"{pid}:{lang} hint neither states {silent} as a placeholder nor declares it in hint_omits"
    )


@pytest.mark.parametrize("pid", sorted(ROWS), ids=sorted(ROWS))
def test_a_declared_omission_is_a_task_parameter_left_unstated_for_a_reason(pid: str) -> None:
    """An omission naming nothing, naming what the hint states, or naming a parameter
    its role already excuses, is stale: the role is the reason (audit C1)."""
    meta = ROWS[pid]
    for name, reason in meta.hint_omits.items():
        assert name in _properties(pid), f"{pid}: hint_omits names {name!r}, not a parameter"
        role = roles(PROCEDURES[pid].params_model()).get(name)
        assert role in STATED_ROLES, f"{pid}: {name!r} is a {role} parameter, excused by its role"
        assert reason.strip(), f"{pid}: hint_omits gives {name!r} no reason"
        for lang, hint in meta.prompt_hints.items():
            assert name not in placeholders(hint), f"{pid}:{lang} states omitted {name!r}"


def test_an_excused_role_carries_its_reason() -> None:
    """Every role a hint may leave unstated is one `unstated` can give a reason for."""
    reasons = unstated(PROCEDURES["n_plus_7"].params_model(), {})
    assert reasons["source"] == ROLES["material"]
    assert reasons["ambiguous_nouns"] == ROLES["policy"]
    assert "offset" not in reasons
    assert all(ROLES[role].strip() for role in ROLES)


def test_a_rows_own_omission_wins_over_its_roles() -> None:
    """`hint_omits` speaks for the row; a role's reason is the fallback."""
    reasons = unstated(PROCEDURES["n_plus_7"].params_model(), {"offset": "a reason"})
    assert reasons["offset"] == "a reason"


def test_a_minted_parameter_reaches_the_prompt() -> None:
    """The case the renderer exists for: a value other than the default."""
    assert '"q"' in prompt_hint("lipogram", forbidden="q")
    assert '"q"' not in prompt_hint("lipogram")


def _setting(pid: str, name: str, value: str) -> str:
    """The line a hint appends for a parameter it does not carry, set off its default."""
    description = PROCEDURES[pid].params_model().model_fields[name].description
    return f"- {name} = {value}: {description}"


def test_a_threshold_the_template_does_not_carry_is_stated_when_set() -> None:
    """R-F3: a switch or threshold set off its default changes what the checker
    judges, so the prompt says so. Dropped, `dead` read as an answer the hint
    allowed and the checker refused as `too_short`."""
    default = prompt_hint("eodermdrome")
    assert prompt_hint("eodermdrome", min_letters=12) == "\n".join(
        [default, _setting("eodermdrome", "min_letters", "12")]
    )
    assert check("eodermdrome", "dead", min_letters=12).satisfied is False


def test_each_set_parameter_gets_its_own_line_in_field_order() -> None:
    lines = prompt_hint("word_ladder", target="warm", end_at_target=True, min_steps=3).split("\n")
    assert lines == [
        prompt_hint("word_ladder"),
        _setting("word_ladder", "target", "warm"),
        _setting("word_ladder", "min_steps", "3"),
        _setting("word_ladder", "end_at_target", "True"),
    ]


def test_a_parameter_given_its_default_value_adds_nothing() -> None:
    """Byte-identical: stating the default is not setting anything."""
    assert prompt_hint("eodermdrome", min_letters=2) == prompt_hint("eodermdrome")
    assert prompt_hint("word_ladder", end_at_target=False) == prompt_hint("word_ladder")


def test_render_hint_states_what_the_callers_template_leaves_out() -> None:
    template = "Write a ladder ending on {target}."
    rendered = render_hint("word_ladder", template, target="warm", min_steps=3)
    assert rendered == "\n".join(
        ["Write a ladder ending on warm.", _setting("word_ladder", "min_steps", "3")]
    )
    assert render_hint("word_ladder", template, target="warm") == "Write a ladder ending on warm."


def test_a_composite_states_its_constraints_parameters_once() -> None:
    """`constraint_params` is stated by each constraint's own line, not again as a
    setting; a constraint's own setting is indented under its line."""
    composite: dict[str, Any] = {
        "constraints": ["lipogram", "eodermdrome"],
        "constraint_params": {"lipogram": {"forbidden": "q"}, "eodermdrome": {"min_letters": 9}},
    }
    lines = prompt_hint("multiple_constraint", **composite).split("\n")
    assert lines[1:] == [
        "- " + prompt_hint("lipogram", forbidden="q"),
        "- " + prompt_hint("eodermdrome"),
        "  " + _setting("eodermdrome", "min_letters", "9"),
    ]


#: Flips a row refuses without another parameter: `end_at_target` needs a `target`,
#: and `test_each_set_parameter_gets_its_own_line_in_field_order` states it with one.
REFUSED_ALONE = {("word_ladder", "end_at_target")}


def _flippable() -> list[tuple[str, str]]:
    """Each boolean parameter a hint does not carry, on rows whose hint renders bare."""
    found: list[tuple[str, str]] = []
    for pid, lang in IMPLEMENTED_HINTS:
        if lang != "en" or PROCEDURES[pid].params_schema().get("required"):
            continue
        model = PROCEDURES[pid].params_model()
        if set(placeholders(ROWS[pid].prompt_hints[lang])) - set(default_values(model)):
            continue
        stated = set(placeholders(ROWS[pid].prompt_hints[lang]))
        for name, field in model.model_fields.items():
            if name not in stated and isinstance(field.default, bool):
                found.append((pid, name))
    return found


@pytest.mark.parametrize(("pid", "name"), _flippable(), ids=[f"{p}.{n}" for p, n in _flippable()])
def test_no_parameter_set_off_its_default_is_dropped(pid: str, name: str) -> None:
    """The rule, on every row it can be asked of without inventing a value: flip a
    boolean the template does not carry, and the prompt names it."""
    flipped = not PROCEDURES[pid].params_model().model_fields[name].default
    params: dict[str, Any] = {name: flipped}
    if (pid, name) in REFUSED_ALONE:
        with pytest.raises(InvalidParams):
            prompt_hint(pid, **params)
        return
    rendered = prompt_hint(pid, **params)
    assert rendered.split("\n")[-1] == _setting(pid, name, str(flipped))


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
    assert rendered == ROWS["every_nth_word"].prompt_hints["en"].format(n=3)
    assert rendered != ROWS["every_nth_word"].prompt_hints["en"].format(n=7)


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
    unhinted = [pid for pid in COMPOSITE["constraints"] if "de" not in ROWS[pid].prompt_hints]
    assert unhinted, "give the composite a constraint with no German hint"
    with pytest.raises(NoPromptHint) as raised:
        prompt_hint("multiple_constraint", lang="de", **COMPOSITE)
    assert raised.value.detail() == {"procedure_id": unhinted[0], "lang": "de"}


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


#: A quoted literal: straight or curly, double or single. A straight single quote
#: opens only where no letter precedes it and closes only where none follows, so
#: the apostrophes of "don't" and "one's" are not quotes. A curly closing quote
#: doubles as the typographic apostrophe, so it closes only before a non-letter.
#: One holding a placeholder quotes the caller's value ("{forbidden}") and is skipped.
QUOTED = re.compile(
    r"\"([^\"]*)\""
    r"|\u201c([^\u201d]*)\u201d"
    r"|(?<!\w)'([^'\s](?:[^']*\S)?)'(?!\w)"
    r"|\u2018(.+?)\u2019(?!\w)"
)
#: The phrase an example marker introduces, up to the next clause punctuation.
EXAMPLE_PHRASE = re.compile(
    r"\b(?:such as|as in|e\.g\.|for example|for instance|like),?\s+([^;:.()]+?)(?=[,;:.()]|$)",
    re.IGNORECASE,
)
#: "as stressed spells desserts": an example given as a worked transformation.
WORKED_EXAMPLE = re.compile(r"\bas (\w+) (?:spells|becomes|reads|turns into) (\w+)", re.IGNORECASE)
_QUOTE_MARKS = "\"'\u201c\u2018"


def hint_examples(hint: str) -> list[str]:
    """Every example a hint offers: quoted literals, listed items and worked examples."""
    found = [
        literal
        for match in QUOTED.finditer(hint)
        if (literal := next((group for group in match.groups() if group), ""))
        and "{" not in literal
    ]
    for match in EXAMPLE_PHRASE.finditer(hint):
        phrase = match.group(1)
        if not any(mark in phrase for mark in _QUOTE_MARKS):
            found += [item.strip() for item in re.split(r",| or | and ", phrase) if item.strip()]
    for match in WORKED_EXAMPLE.finditer(hint):
        found += [match.group(1), match.group(2)]
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


@pytest.mark.parametrize(
    ("hint", "expected"),
    [
        ('Omit "{forbidden}" and write "abso-bloody-lutely".', ["abso-bloody-lutely"]),
        ("Write \u201ctartar\u201d.", ["tartar"]),
        ("Write 'tartar' twice.", ["tartar"]),
        ("Write \u2018tartar\u2019 twice.", ["tartar"]),
        ("Use doubled words, such as tartar or couscous.", ["tartar", "couscous"]),
        ("Split words, as in abso bloody lutely.", ["abso bloody lutely"]),
        ("Use doubled words, e.g. couscous.", ["couscous"]),
        ("Use doubled words, for example couscous.", ["couscous"]),
        ("Use doubled words, for instance couscous.", ["couscous"]),
        ("Use doubled words like couscous.", ["couscous"]),
        # The 88d8b49 semordnilap hint: the leak the guard exists for.
        (
            "Write a list of words and nothing else, every one of them spelling a different"
            " word backwards, as stressed spells desserts.",
            ["stressed", "desserts"],
        ),
        ("Change a letter, as cat becomes cut.", ["cat", "cut"]),
        # Apostrophes inside or after a word are not quotes.
        ("Don't repeat one's words or the writers' lines.", []),
        ("Don\u2019t repeat one\u2019s words.", []),
    ],
)
def test_hint_examples_finds_every_kind_of_example(hint: str, expected: list[str]) -> None:
    assert hint_examples(hint) == expected


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
