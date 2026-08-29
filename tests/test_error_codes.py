"""Every failure the agentic surface can return must be labelled.

A model cannot act on a traceback. It can act on
`{"code": "invalid_params", "detail": {...}}`.
"""

import inspect
from typing import Any

import pytest

from denckring.core import errors
from denckring.core.errors import (
    DenckringError,
    InvalidParams,
    MissingCapability,
    NoCandidateWord,
    UnknownProcedure,
)
from denckring.core.protocol import Constructive
from denckring.core.registry import get


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


def test_there_are_nineteen_subclasses() -> None:
    """Pins the inventory. If this fails, a class was added or removed and the
    codes table in the spec needs the same edit.

    Sixteen until `apply` grew a spine: `DegenerateOutput` for a generator that
    returned its own input, and `InputTooShort` for the four that did so because
    the input could not feed them. Eighteen until `NotConstructive` replaced the
    dict the MCP tool built by hand for a procedure with no generator.
    """
    assert len(subclasses()) == 19


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


def test_missing_capability_promises_no_extra_that_does_not_exist() -> None:
    """The remedy has to be one the reader can follow.

    French is a built-in pack with no lexicon (ADR 0029), so every lexicon row fails
    through this error — and the message used to interpolate the language into
    `pip install denckring[{lang}]`, sending a French caller after a distribution
    that has never existed. English and German have one; nothing else does.
    """
    payload = MissingCapability("n_plus_7", "fr", "lexicon.nouns").to_dict()
    assert "denckring[fr]" not in payload["message"]
    assert "lexicon.nouns" in payload["message"]
    assert payload["detail"]["lang"] == "fr"


def test_invalid_params_carries_the_field_errors() -> None:
    from denckring import check

    with pytest.raises(InvalidParams) as caught:
        check("pangrammatic_window", "text", max_length=3)
    payload = caught.value.to_dict()
    assert payload["code"] == "invalid_params"
    assert payload["detail"]


def _refusal(procedure_id: str, text: str, **params: Any) -> dict[str, Any]:
    """Drive a real generator into refusing, and return what a JSON caller sees.

    Constructing `NoCandidateWord` by hand with a hardcoded string, which this
    test used to do, asserts only that the class stores what it is handed. It
    cannot notice a call site that stopped passing a reason, or one that never
    passed one — which is the entire thing ruling R17 was about.
    """
    procedure = get(procedure_id)
    assert isinstance(procedure, Constructive)
    with pytest.raises(NoCandidateWord) as exc_info:
        procedure.apply(text, **params)
    return exc_info.value.to_dict()


def test_no_candidate_word_reason_replaces_the_lexicon_default() -> None:
    """`paragram` (the original caller) gets the unset-`reason` default, unchanged.
    `diastic` and `mesostic` (added in the selection cluster) pass a reason
    describing what actually offered nothing — a source word, not a lexicon swap
    — so a model reading the payload is told the true cause, not paragram's.

    Driven through the real `apply` calls: what is under test is that each call
    site supplies its own reason, not that the constructor keeps a string.
    """
    paragram = _refusal("paragram", "zzz")
    diastic = _refusal("diastic", "zzz", seed_phrase="q")
    mesostic = _refusal("mesostic", "zzz", spine="q")

    for payload in (paragram, diastic, mesostic):
        assert payload["code"] == "no_candidate_word"

    messages = {paragram["message"], diastic["message"], mesostic["message"]}
    assert len(messages) == 3, "all three messages should differ"
    assert "lexicon" in paragram["message"]
    assert "lexicon" not in diastic["message"]
    assert "lexicon" not in mesostic["message"]


def test_no_candidate_word_reason_reaches_the_json_not_only_the_message() -> None:
    """R17 exists so an agentic caller learns the true cause. `detail()` returned
    `{"procedure_id": ...}` alone and `reason` was never even stored on the
    instance, so the cause was reachable only by parsing English out of
    `message` — which is what `to_dict` exists to spare a caller.
    """
    diastic = _refusal("diastic", "zzz", seed_phrase="q")
    assert "seed phrase" in diastic["detail"]["reason"]
    assert diastic["detail"]["reason"] in diastic["message"]

    mesostic = _refusal("mesostic", "zzz", spine="q")
    assert "spine" in mesostic["detail"]["reason"]

    paragram = _refusal("paragram", "zzz")
    assert "lexicon" in paragram["detail"]["reason"]

    reasons = {row["detail"]["reason"] for row in (paragram, diastic, mesostic)}
    assert len(reasons) == 3, "each call site must name its own cause"
