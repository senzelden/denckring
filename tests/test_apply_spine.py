"""`apply` gets the checks `check` has had all along.

Before this, every generator hand-rolled its own preamble and each forgot
something different: `cut_up` never validated parameters, four hand-rolled
`require_capability`, and all 27 let `seed` bind to the signature where pydantic
could never see it.
"""

from typing import Any

import pytest

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams
from denckring.core.errors import InvalidParams
from denckring.core.registry import get


def cut_up() -> ConstructiveProcedure[Any, Any]:
    """`get` is typed as the base class, which has no `apply` — narrow it once here.

    The same `assert isinstance` every other suite does before calling a
    generator; only the type it narrows to has moved.
    """
    procedure = get("cut_up")
    assert isinstance(procedure, ConstructiveProcedure)
    return procedure


def test_cut_up_is_on_the_spine() -> None:
    assert isinstance(get("cut_up"), ConstructiveProcedure)


def test_cut_up_refuses_an_unknown_parameter() -> None:
    """It accepted anything at all, because it never called parse_params."""
    with pytest.raises(InvalidParams) as caught:
        cut_up().apply("one two three four", nonsense=1)
    assert "nonsense" in str(caught.value)


def test_seed_is_type_checked_now_it_is_a_field() -> None:
    """As a signature keyword it bound before `**params` and was never validated,
    so every generator accepted `seed="not-an-int"`."""
    with pytest.raises(InvalidParams):
        cut_up().apply("one two three four", seed="not-an-int")


def test_seed_still_fixes_the_draw() -> None:
    text = "one two three four five six seven eight"
    assert cut_up().apply(text, seed=7) == cut_up().apply(text, seed=7)


def test_the_mixins_carry_what_they_say() -> None:
    assert SeedParams.model_fields["seed"].default is None
    assert ApplyParams.model_fields["allow_identity"].default is False


def test_apply_params_are_visible_to_a_non_python_caller() -> None:
    """The point of a field over a signature keyword: it reaches the schema."""
    schema = cut_up().apply_params_model().model_json_schema()
    assert "seed" in schema["properties"]
