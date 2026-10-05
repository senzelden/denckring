"""A schema a caller can draw from, which never refuses what `check` accepts (audit B5).

A consumer minting parameters could not mint `calculator_word`, `proteus_verse`,
`llull_figure` or `quenina` from their schemas: `digits`, `metre` and `figure` were
bare strings and `n` a bare integer, though the checker refuses most values of the
first three and fails most values of the last. The schemas now say so. The rule for
0.3.2 is that a schema may only restate what validation already does: a JSON Schema
keyword that validates may refuse only values `check` refuses, never one it accepts.
These tests hold that for every such keyword on every row, so a keyword added later
is held to it without being listed here.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from denckring import check, golden_cases
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DenckringError, MissingCapability
from denckring.core.fields import VALID_KEY
from denckring.core.registry import all_procedures
from denckring.eval.harness import GoldenCase
from denckring.procedures.quenina import VALID_CAP, is_valid_size

PROCEDURES = all_procedures()

#: The keywords that refuse a value. Any of them on a field puts it under the rule.
VALIDATING = frozenset(
    {
        "enum",
        "const",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minItems",
        "maxItems",
        "format",
    }
)

#: The keywords `_meets` evaluates. A validating keyword outside it fails the test
#: rather than passing unchecked.
EVALUATED = frozenset({"enum", "pattern", "minLength", "maxLength", "minimum", "maximum"})

#: Keywords that state the accepted set exactly, so the schema accepting a value
#: means `check` does too. `minLength` on `sonnet.scheme` is only a necessary bound.
EXACT = frozenset({"enum", "pattern"})


def _extra(model: Any, name: str) -> dict[str, Any]:
    extra = model.model_fields[name].json_schema_extra
    return dict(extra) if isinstance(extra, dict) else {}


def _stated(keys: frozenset[str]) -> list[tuple[str, str]]:
    """Every (row, field) whose own schema adds one of `keys`, on the checker's model.

    Read from `json_schema_extra`, where a field states what pydantic does not
    enforce; a keyword pydantic writes from `ge`, `le` or a `Literal` is the
    validation itself and cannot disagree with it.
    """
    return [
        (pid, name)
        for pid, procedure in sorted(PROCEDURES.items())
        for name in procedure.params_model().model_fields
        if keys & set(_extra(procedure.params_model(), name))
    ]


def _case(pid: str) -> GoldenCase:
    """A case this install can run, so a refusal is about the parameter."""
    cases = [case for case in golden_cases() if case.procedure == pid]
    assert cases, f"{pid} has no runnable golden case to probe its schema with"
    return cases[0]


def _accepted(case: GoldenCase, name: str, value: Any) -> bool:
    """Whether `check` takes the value, judging the text rather than refusing the call."""
    try:
        check(case.procedure, case.text, lang=case.lang, **{**case.params, name: value})
    except MissingCapability:
        raise
    except DenckringError:
        return False
    return True


def _meets(keywords: dict[str, Any], value: Any) -> bool:
    """A JSON Schema check of the keywords this file evaluates, on one value.

    `pattern` is matched with `re.search`, as Python's `jsonschema` matches it, so a
    pattern that is anchored only under ECMA-262 (where `$` never matches before a
    trailing newline) fails here rather than in a Python consumer.
    """
    if "enum" in keywords and value not in keywords["enum"]:
        return False
    if isinstance(value, str):
        if "pattern" in keywords and not re.search(keywords["pattern"], value):
            return False
        if len(value) < keywords.get("minLength", 0):
            return False
        if "maxLength" in keywords and len(value) > keywords["maxLength"]:
            return False
    if isinstance(value, int | float) and not isinstance(value, bool):
        if "minimum" in keywords and value < keywords["minimum"]:
            return False
        if "maximum" in keywords and value > keywords["maximum"]:
            return False
    return True


def _probes(case: GoldenCase, name: str, keywords: dict[str, Any]) -> list[Any]:
    """Values near every edge the keywords draw: theirs, the case's, and their neighbours."""
    field = PROCEDURES[case.procedure].params_model().model_fields[name]
    default = None if field.is_required() else field.get_default(call_default_factory=True)
    found = [case.params.get(name), default, *keywords.get("enum", [])]
    found += keywords.get("examples", [])
    strings = ["", "0", "2", "7", "٣", "73532", "x", "A" * 13, "A" * 14, "1" * 14, "../x"]
    near = [f"{value}x" for value in found if isinstance(value, str)]
    near += [value.upper() for value in found if isinstance(value, str)]
    # A trailing newline, which `$` admits under Python's regex semantics.
    near += [f"{value}\n" for value in found if isinstance(value, str)]
    return [value for value in [*found, *strings, *near] if value is not None]


STATED = _stated(VALIDATING)


def test_the_rows_the_audit_could_not_mint_now_say_what_they_take() -> None:
    """The four this chapter gave a validating keyword, so the rule is not vacuous."""
    assert {("calculator_word", "digits"), ("llull_figure", "figure")} <= set(STATED)
    assert {("proteus_verse", "metre"), ("sonnet", "scheme")} <= set(STATED)


@pytest.mark.parametrize(("pid", "name"), STATED, ids=[f"{p}.{n}" for p, n in STATED])
def test_a_keyword_refuses_only_what_check_refuses(pid: str, name: str) -> None:
    keywords = _extra(PROCEDURES[pid].params_model(), name)
    unevaluated = (VALIDATING & set(keywords)) - EVALUATED
    assert not unevaluated, f"{pid}.{name}: teach `_meets` {sorted(unevaluated)} first"
    case = _case(pid)
    for value in _probes(case, name, keywords):
        accepted = _accepted(case, name, value)
        if accepted:
            assert _meets(keywords, value), f"{pid}.{name}: schema refuses {value!r}"
        elif EXACT & set(keywords):
            assert not _meets(keywords, value), f"{pid}.{name}: schema admits {value!r}"

    annotation = PROCEDURES[pid].params_model().model_fields[name].annotation
    values = st.integers(-5, 200) if annotation in (int, int | None) else st.text(max_size=20)

    @settings(max_examples=150, derandomize=True, deadline=None)
    @given(values)
    def holds(value: Any) -> None:
        if _accepted(case, name, value):
            assert _meets(keywords, value), f"{pid}.{name}: schema refuses {value!r}"
        elif EXACT & set(keywords):
            assert not _meets(keywords, value), f"{pid}.{name}: schema admits {value!r}"

    holds()


EXAMPLED = _stated(frozenset({"examples"}))


@pytest.mark.parametrize(("pid", "name"), EXAMPLED, ids=[f"{p}.{n}" for p, n in EXAMPLED])
def test_every_example_is_a_value_check_accepts(pid: str, name: str) -> None:
    """An example is what a caller drawing a value draws first; it must not refuse."""
    case = _case(pid)
    for example in _extra(PROCEDURES[pid].params_model(), name)["examples"]:
        assert _accepted(case, name, example), f"{pid}.{name}: example {example!r} is refused"


def test_apply_models_restate_nothing_their_checker_does_not() -> None:
    """The rule is held on the checker's model; an apply model inherits it or adds none."""
    for pid, procedure in PROCEDURES.items():
        if not isinstance(procedure, ConstructiveProcedure):
            continue
        model = procedure.apply_params_model()
        for name in model.model_fields:
            added = VALIDATING & set(_extra(model, name))
            if added:
                assert (pid, name) in STATED, f"{pid}.{name}: {sorted(added)} on apply only"


def test_quenina_lists_exactly_the_sizes_the_form_exists_for() -> None:
    """`x-denckring-valid` is a promise about the checker, not a copy of a helper:
    a listed size never fails as `invalid_size`, and an unlisted one up to the cap
    always does."""
    listed = PROCEDURES["quenina"].params_schema()["properties"]["n"][VALID_KEY]
    # One distinct end-word per line, enough lines for every size, so the size is
    # judged rather than the text's length.
    text = "\n".join("x" * width for width in range(1, VALID_CAP + 1))
    for size in range(1, VALID_CAP + 1):
        rules = {v.rule for v in check("quenina", text, n=size).violations}
        assert ("invalid_size" in rules) is (size not in listed), size
    assert listed == [size for size in range(1, VALID_CAP + 1) if is_valid_size(size)]
    assert listed[:7] == [1, 2, 3, 5, 6, 9, 11]


@pytest.mark.parametrize("size", [0, -1, -5])
def test_quenina_fails_a_size_below_one(size: int) -> None:
    """The schema states no `minimum` for `n`, so a caller drawing from an integer range
    can pass a size below one. It must fail as `invalid_size`: a negative size once
    passed, because the spiral was empty and the size itself was counted as matched."""
    report = check("quenina", "a\nb\nc\nd", n=size)
    assert report.satisfied is False, size
    assert report.score < 1.0, size
    assert [v.rule for v in report.violations] == ["invalid_size"], size
