"""What a generator turned out. `Report`'s counterpart for the other half."""

from denckring.core.errors import NotConstructive
from denckring.core.protocol import Production


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
