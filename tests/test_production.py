"""What a generator turned out. `Report`'s counterpart for the other half."""

from typing import Any

import pytest
from pydantic import ValidationError

import denckring
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DegenerateOutput, InvalidParams, NotConstructive, UnknownProcedure
from denckring.core.protocol import Candidate, Production
from denckring.core.registry import all_procedures, get


def constructive(pid: str) -> ConstructiveProcedure[Any, Any]:
    """`get` is typed as the checking base, which has no `produce` — narrow it
    once here, the same way `test_apply_spine.py` does for `apply`."""
    procedure = get(pid)
    assert isinstance(procedure, ConstructiveProcedure)
    return procedure


def test_production_carries_what_a_caller_needs() -> None:
    produced = Production(
        procedure="paragram", candidates=[Candidate(text="a"), Candidate(text="b")]
    )
    assert produced.procedure == "paragram"
    assert produced.texts == ["a", "b"]
    assert produced.truncated is False
    assert produced.metrics == {}


def test_truncated_is_carried_when_set() -> None:
    produced = Production(procedure="anagram", candidates=[Candidate(text="a")], truncated=True)
    assert produced.truncated is True


def test_it_serialises_for_a_caller_who_never_touches_python() -> None:
    """The reason this is a pydantic model and not a tuple."""
    dumped = Production(
        procedure="cut_up", candidates=[Candidate(text="a")], metrics={"found": 3.0}
    ).model_dump()
    assert dumped == {
        "procedure": "cut_up",
        "candidates": [{"text": "a", "metrics": {}}],
        "truncated": False,
        "metrics": {"found": 3.0},
        "texts": ["a"],
    }


def test_not_constructive_names_the_procedure() -> None:
    error = NotConstructive("lipogram")
    assert error.code == "not_constructive"
    assert error.to_dict()["detail"]["procedure_id"] == "lipogram"
    assert "lipogram" in str(error)


def test_texts_may_not_be_empty() -> None:
    """`apply` reads `texts[0]`; an empty list should fail loudly here, naming
    the field, rather than raise a bare `IndexError` from that line."""
    with pytest.raises(ValidationError, match="candidates"):
        Production(procedure="paragram", candidates=[])


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


#: Every generator, because the property below is about every generator and
#: `cut_up` alone would pass with the field missing from the other 26.
CONSTRUCTIVE = sorted(
    pid
    for pid, procedure in all_procedures().items()
    if isinstance(procedure, ConstructiveProcedure)
)


def test_there_are_generators_to_range_over() -> None:
    """An empty parametrisation generates no test items and passes in silence."""
    assert CONSTRUCTIVE


@pytest.mark.parametrize("pid", CONSTRUCTIVE)
def test_max_results_is_a_parameter_of_every_generator(pid: str) -> None:
    """Named `pid` rather than `procedure_id`: conftest parametrises that name
    over the whole registry, and pytest errors on the duplicate."""
    assert constructive(pid).apply_params_model().model_fields["max_results"].default == 10


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


def test_a_drawing_generator_returns_one_sample_per_call() -> None:
    """What `truncated` means on the ten rows that draw. One sample is the whole
    production, so nothing was cut off — `texts` is not used for n draws, and a
    caller wanting a second sample calls again with another seed. Documented on
    the field and in ADR 0026; pinned here so the two cannot drift apart."""
    produced = constructive("cut_up").produce(
        "one two three four five six seven eight", seed=7, max_results=10
    )
    assert len(produced.texts) == 1
    assert produced.truncated is False
    assert produced.metrics["found"] == 1.0


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


def test_production_exposes_texts_derived_from_candidates() -> None:
    production = Production(
        procedure="anagram",
        candidates=[Candidate(text="room dirty", metrics={"max_band": 50.0})],
    )
    assert production.texts == ["room dirty"]


def test_texts_survives_serialisation_so_the_json_surface_is_unchanged() -> None:
    """`apply --json` and the MCP surface both read `texts`. A plain @property
    would vanish from model_dump() and break them silently."""
    production = Production(procedure="anagram", candidates=[Candidate(text="tinsel")])
    assert production.model_dump()["texts"] == ["tinsel"]


def test_a_production_with_no_candidates_is_a_validation_error() -> None:
    """`min_length` moved from `texts` to `candidates` with the data. Without it
    `apply`'s `texts[0]` is a bare IndexError rather than a named field error."""
    with pytest.raises(ValidationError):
        Production(procedure="anagram", candidates=[])
