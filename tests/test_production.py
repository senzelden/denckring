"""What a generator turned out. `Report`'s counterpart for the other half."""

from typing import Any

import pytest
from pydantic import ValidationError

import denckring
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DegenerateOutput, InvalidParams, NotConstructive, UnknownProcedure
from denckring.core.protocol import Production
from denckring.core.registry import get


def constructive(pid: str) -> ConstructiveProcedure[Any, Any]:
    """`get` is typed as the checking base, which has no `produce` — narrow it
    once here, the same way `test_apply_spine.py` does for `apply`."""
    procedure = get(pid)
    assert isinstance(procedure, ConstructiveProcedure)
    return procedure


def test_production_carries_what_a_caller_needs() -> None:
    produced = Production(procedure="paragram", texts=["a", "b"])
    assert produced.procedure == "paragram"
    assert produced.texts == ["a", "b"]
    assert produced.truncated is False
    assert produced.metrics == {}


def test_truncated_is_carried_when_set() -> None:
    assert Production(procedure="anagram", texts=["a"], truncated=True).truncated is True


def test_it_serialises_for_a_caller_who_never_touches_python() -> None:
    """The reason this is a pydantic model and not a tuple."""
    dumped = Production(procedure="cut_up", texts=["a"], metrics={"found": 3.0}).model_dump()
    assert dumped == {
        "procedure": "cut_up",
        "texts": ["a"],
        "truncated": False,
        "metrics": {"found": 3.0},
    }


def test_not_constructive_names_the_procedure() -> None:
    error = NotConstructive("lipogram")
    assert error.code == "not_constructive"
    assert error.to_dict()["detail"]["procedure_id"] == "lipogram"
    assert "lipogram" in str(error)


def test_texts_may_not_be_empty() -> None:
    """`apply` reads `texts[0]`; an empty list should fail loudly here, naming
    the field, rather than raise a bare `IndexError` from that line."""
    with pytest.raises(ValidationError, match="texts"):
        Production(procedure="paragram", texts=[])


def test_produce_returns_a_production_for_a_single_result_generator() -> None:
    produced = constructive("every_nth_word").produce("one two three four", n=2)
    assert produced.procedure == "every_nth_word"
    assert produced.texts == ["two four"]
    assert produced.truncated is False


def test_apply_is_the_first_text() -> None:
    """The string surface is defined in terms of the structured one, not beside it."""
    procedure = constructive("every_nth_word")
    assert (
        procedure.apply("one two three four", n=2)
        == procedure.produce("one two three four", n=2).texts[0]
    )


def test_max_results_is_a_parameter_of_every_generator() -> None:
    assert constructive("cut_up").apply_params_model().model_fields["max_results"].default == 10


def test_max_results_below_one_is_refused() -> None:
    """Zero results is not a smaller answer, it is no answer — and `texts[0]`
    would raise IndexError rather than say so."""
    with pytest.raises(InvalidParams):
        constructive("every_nth_word").produce("one two three four", n=2, max_results=0)


def test_the_guard_still_refuses_when_nothing_survives() -> None:
    """A single-result generator whose one candidate is degenerate must behave
    exactly as it did before the guard learned to filter."""
    with pytest.raises(DegenerateOutput):
        constructive("every_nth_word").produce("one two three", n=1)


def test_metrics_report_what_was_found() -> None:
    produced = constructive("every_nth_word").produce("one two three four", n=2)
    assert produced.metrics["found"] == 1.0


def test_the_package_exports_both_surfaces() -> None:
    """`check` has been exported since the beginning and `apply` never was, so
    every Python caller reached through the registry to generate anything."""
    assert denckring.apply("every_nth_word", "one two three four", n=2) == "two four"
    produced = denckring.produce("every_nth_word", "one two three four", n=2)
    assert produced.texts == ["two four"]
    assert "apply" in denckring.__all__
    assert "produce" in denckring.__all__


def test_generating_with_a_checker_only_procedure_is_an_error_not_a_dict() -> None:
    with pytest.raises(NotConstructive):
        denckring.apply("lipogram", "a text")
    with pytest.raises(NotConstructive):
        denckring.produce("lipogram", "a text")


def test_an_unknown_id_still_raises_unknown_procedure() -> None:
    with pytest.raises(UnknownProcedure):
        denckring.produce("no_such_procedure", "a text")
