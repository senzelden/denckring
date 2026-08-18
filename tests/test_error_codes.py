"""Every failure the agentic surface can return must be labelled.

A model cannot act on a traceback. It can act on
`{"code": "invalid_params", "detail": {...}}`.
"""

import inspect

import pytest

from denckring.core import errors
from denckring.core.errors import (
    DenckringError,
    InvalidParams,
    MissingCapability,
    NoCandidateWord,
    UnknownProcedure,
)


def subclasses() -> list[type[DenckringError]]:
    return [
        value
        for _, value in inspect.getmembers(errors, inspect.isclass)
        if issubclass(value, DenckringError) and value is not DenckringError
    ]


def test_every_subclass_has_a_code() -> None:
    """A subclass added later without a code would reach a model unlabelled."""
    missing = [cls.__name__ for cls in subclasses() if not getattr(cls, "code", "")]
    assert not missing, f"no code on: {missing}"


def test_codes_are_unique() -> None:
    codes = [cls.code for cls in subclasses()]
    duplicates = {code for code in codes if codes.count(code) > 1}
    assert not duplicates, f"duplicate codes: {duplicates}"


def test_there_are_fourteen_subclasses() -> None:
    """Pins the inventory. If this fails, a class was added or removed and the
    codes table in the spec needs the same edit."""
    assert len(subclasses()) == 14


def test_to_dict_carries_code_and_message() -> None:
    payload = UnknownProcedure("nosuch").to_dict()
    assert payload["code"] == "unknown_procedure"
    assert "nosuch" in payload["message"]


def test_unknown_procedure_suggests_near_matches() -> None:
    """The single most likely model error is a slightly wrong id."""
    payload = UnknownProcedure("lipogramm").to_dict()
    assert "lipogram" in payload["detail"]["suggestions"]


def test_unknown_procedure_survives_a_hopeless_id() -> None:
    payload = UnknownProcedure("zzzzzz").to_dict()
    assert payload["detail"]["suggestions"] == []


def test_missing_capability_names_the_extra_that_supplies_it() -> None:
    payload = MissingCapability("dactylic_hexameter", "en", "stress").to_dict()
    assert payload["code"] == "missing_capability"
    assert payload["detail"]["capability"] == "stress"
    assert "denckring[en]" in payload["message"]


def test_invalid_params_carries_the_field_errors() -> None:
    from denckring import check

    with pytest.raises(InvalidParams) as caught:
        check("pangrammatic_window", "text", max_length=3)
    payload = caught.value.to_dict()
    assert payload["code"] == "invalid_params"
    assert payload["detail"]


def test_no_candidate_word_reason_replaces_the_lexicon_default() -> None:
    """`paragram` (the original caller) gets the unset-`reason` default, unchanged.
    `diastic` and `mesostic` (added in the selection cluster) pass a reason
    describing what actually offered nothing — a source word, not a lexicon swap
    — so a model reading the message is told the true cause, not paragram's."""
    paragram = NoCandidateWord("paragram").to_dict()
    diastic = NoCandidateWord(
        "diastic", "no word in the source carries the seed phrase's first letter"
    ).to_dict()
    mesostic = NoCandidateWord(
        "mesostic", "no word in the source carries the spine's first letter"
    ).to_dict()

    for payload in (paragram, diastic, mesostic):
        assert payload["code"] == "no_candidate_word"
        assert payload["detail"]

    messages = {paragram["message"], diastic["message"], mesostic["message"]}
    assert len(messages) == 3, "all three messages should differ"
    assert "lexicon" in paragram["message"]
    assert "lexicon" not in diastic["message"]
    assert "lexicon" not in mesostic["message"]
