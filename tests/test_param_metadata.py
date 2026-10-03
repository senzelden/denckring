"""Every parameter says what it is: its role in the task and, for a string, its kind.

A consumer minting parameters for every row told five meanings of a `None` default
apart by reading prose, and registered a sampler per (row, parameter) because
`forbidden` is a letter on one row and a word on another (audit C1, C5). These
tests hold the declarations to rules a fresh row cannot slip past: every field of
every model declares a role from the closed set, every free string a kind, and the
kinds agree with the values the golden corpus actually passes.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, Field

from denckring import describe, golden_cases
from denckring.core.base import ConstructiveProcedure
from denckring.core.fields import (
    KIND_KEY,
    KINDS,
    ROLE_KEY,
    ROLES,
    holds_strings,
    kinds,
    param,
    roles,
)
from denckring.core.registry import all_procedures
from denckring.lang import get_pack

PROCEDURES = all_procedures()


def _models(pid: str) -> list[type[BaseModel]]:
    procedure = PROCEDURES[pid]
    models: list[type[BaseModel]] = [procedure.params_model()]
    if isinstance(procedure, ConstructiveProcedure):
        models.append(procedure.apply_params_model())
    return models


@pytest.mark.parametrize("pid", sorted(PROCEDURES))
def test_every_field_declares_a_role(pid: str) -> None:
    for model in _models(pid):
        missing = sorted(set(model.model_fields) - set(roles(model)))
        assert not missing, f"{pid}: {model.__name__} declares no {ROLE_KEY} for {missing}"


@pytest.mark.parametrize("pid", sorted(PROCEDURES))
def test_every_free_string_declares_a_kind_and_nothing_else_does(pid: str) -> None:
    for model in _models(pid):
        declared = kinds(model)
        for name, field in model.model_fields.items():
            if holds_strings(field.annotation):
                assert name in declared, f"{pid}: {model.__name__}.{name} declares no {KIND_KEY}"
            else:
                assert name not in declared, f"{pid}: {model.__name__}.{name} is not a string"


@pytest.mark.parametrize("pid", sorted(PROCEDURES))
def test_an_inferred_parameter_defaults_to_none(pid: str) -> None:
    """`inferred` means unset reads it off the text, so unset has to be the default."""
    model = PROCEDURES[pid].params_model()
    for name, role in roles(model).items():
        if role == "inferred":
            field = model.model_fields[name]
            assert not field.is_required() and field.default is None, f"{pid}.{name}"


@pytest.mark.parametrize("pid", sorted(PROCEDURES))
def test_an_apply_only_parameter_is_not_one_check_takes(pid: str) -> None:
    """`apply_only` is a promise that `check` never sees it, so it is not in its model."""
    for name, role in roles(PROCEDURES[pid].params_model()).items():
        assert role != "apply_only", f"{pid}.{name} is on the checker's model"


def test_the_roles_and_kinds_are_published_in_the_schema() -> None:
    """A caller that never touches Python reads them beside the type they qualify."""
    properties = describe("lipogram").params["properties"]
    assert properties["forbidden"][ROLE_KEY] == "task"
    assert properties["forbidden"][KIND_KEY] == "letter"
    assert properties["fold_diacritics"][ROLE_KEY] == "policy"
    assert describe("anagram").apply_params["properties"]["max_nodes"][ROLE_KEY] == "budget"


def test_an_unknown_role_or_kind_is_refused() -> None:
    """Closed sets: a typo is an error when read, not a new role published."""

    class Typo(BaseModel):
        x: str = Field(json_schema_extra={ROLE_KEY: "tsak", KIND_KEY: "letter"})

    class Kindless(BaseModel):
        x: str = Field(json_schema_extra={ROLE_KEY: "task", KIND_KEY: "lettre"})

    with pytest.raises(ValueError, match=f"unknown {ROLE_KEY}"):
        roles(Typo)
    with pytest.raises(ValueError, match=f"unknown {KIND_KEY}"):
        kinds(Kindless)


def test_param_writes_role_kind_and_any_further_schema() -> None:
    assert param("task") == {ROLE_KEY: "task"}
    assert param("task", "letters", examples=["et"]) == {
        ROLE_KEY: "task",
        KIND_KEY: "letters",
        "examples": ["et"],
    }


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (str, True),
        (str | None, True),
        (list[str], True),
        (list[str] | None, True),
        (int, False),
        (list[int], False),
        (dict[str, Any], False),
        (bool | None, False),
    ],
)
def test_holds_strings(annotation: Any, expected: bool) -> None:
    assert holds_strings(annotation) is expected


def _fits(kind: str, value: Any, lang: Any) -> bool:
    """Whether a value a golden case passes reads as its declared kind."""
    if isinstance(value, list):
        return all(_fits(kind, item, lang) for item in value)
    if not isinstance(value, str):
        return False
    pack = get_pack(lang)
    letters = [pack.fold_diacritics(ch) for ch in value if ch.isalpha()]
    vowels = pack.vowels()
    match kind:
        case "letter" | "vowel" | "consonant":
            single = len(value) == 1 and value.isalpha()
            if kind == "vowel":
                return single and letters[0] in vowels
            if kind == "consonant":
                return single and letters[0] not in vowels
            return single
        case "letters":
            return bool(value) and value.isalpha()
        case "vowels":
            return bool(value) and value.isalpha() and all(ch in vowels for ch in letters)
        case "word":
            return bool(value) and not any(ch.isspace() for ch in value)
        case "scheme":
            return any(ch.isalpha() for ch in value)
        case "metre":
            return bool(value) and set(value) <= {"0", "1"}
        case "digits":
            return value.isdigit()
        case _:
            return bool(value.strip())


def test_the_golden_corpus_passes_each_kind_what_it_says() -> None:
    """Measured against the values the corpus actually checks with, so a kind that
    misdescribes its field (a `word` holding a phrase) fails here."""
    seen: set[str] = set()
    wrong: list[str] = []
    for case in golden_cases(runnable=False):
        declared = kinds(PROCEDURES[case.procedure].params_model())
        for name, value in case.params.items():
            if name in declared:
                seen.add(declared[name])
                if not _fits(declared[name], value, case.lang):
                    wrong.append(f"{case.procedure}/{case.name}: {name}={value!r}")
    assert not wrong, wrong
    # The corpus exercises most kinds; the rest are held by the schema alone.
    assert seen <= set(KINDS)
    assert {"letter", "letters", "word", "phrase", "scheme", "text"} <= seen


def test_the_role_reasons_read_as_reasons() -> None:
    """Every role a hint may omit gives `unstated` a sentence to say why."""
    assert all(text.strip() for text in ROLES.values())
    assert all(text.strip() for text in KINDS.values())
