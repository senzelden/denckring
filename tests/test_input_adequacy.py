"""Say what the input lacked, rather than handing it back unchanged.

Four generators returned their input when it could not feed them. That is
indistinguishable from a procedure that ran and changed nothing, which is why
the caller could not tell and neither could the eval.

Six rows raise it now, not four: `spoonerism` called too-few-words
`NoCandidateWord` and `ideenwuerfeln` called too-few-entries `MalformedCorpus`,
which made the code a caller should retry on unpredictable across procedures
that were refusing for the identical reason.
"""

from typing import Any

import pytest

from denckring.core.errors import DenckringError, InputTooShort, counted
from denckring.core.protocol import Constructive
from denckring.core.registry import get

ONE_SENTENCE = "The quick brown fox jumps over the lazy dog and the cat sat still."


#: `boustrophedon` does not draw, so it takes no seed. The other three do.
DRAWN: dict[str, dict[str, Any]] = {
    "cent_mille_milliards": {"seed": 0},
    "recombination": {"seed": 0},
    "wechselsatz": {"seed": 0},
}


def generator(pid: str) -> Constructive:
    """`get` is typed as the checking base, which has no `apply`."""
    procedure = get(pid)
    assert isinstance(procedure, Constructive)
    return procedure


@pytest.mark.parametrize(
    # Named `pid` rather than `procedure_id`: conftest's `pytest_generate_tests`
    # parametrises any argument by that name over the whole registry, and pytest
    # errors on the duplicate rather than choosing between the two.
    "pid",
    ["boustrophedon", "cent_mille_milliards", "recombination", "wechselsatz"],
)
def test_it_says_what_it_needed(pid: str) -> None:
    with pytest.raises(InputTooShort) as caught:
        generator(pid).apply(ONE_SENTENCE, **DRAWN.get(pid, {}))
    detail = caught.value.to_dict()["detail"]
    assert detail["procedure_id"] == pid
    assert detail["needed"]
    assert detail["found"]


def test_the_error_reads_as_a_sentence() -> None:
    error = InputTooShort("boustrophedon", needed="more than one line", found="1 line")
    assert error.code == "input_too_short"
    assert "more than one line" in str(error)
    assert "1 line" in str(error)


def test_the_message_says_what_to_do_next() -> None:
    """`InputTooLong`, `UnknownProcedure`, `MissingCapability` and
    `DegenerateOutput` all end on a remedy; this one stopped at what it found."""
    error = InputTooShort("boustrophedon", needed="more than one line", found="1 line")
    assert "check a text instead of generating from one" in str(error)


def test_the_count_is_pluralised() -> None:
    """`found` was built as `f"{n} line"` at each raise site, so empty input read
    "0 line" — the one string whose job is to say what was handed over."""
    with pytest.raises(InputTooShort) as caught:
        generator("boustrophedon").apply("")
    assert "0 lines" in str(caught.value)
    assert counted(1, "line") == "1 line"
    assert counted(2, "entry", "entries") == "2 entries"


#: Every generator that refuses input for holding too few units, and the input
#: that does it. One code across all of them is the point: `spoonerism` raised
#: `NoCandidateWord` and `ideenwuerfeln` `MalformedCorpus` for exactly the shape
#: `recombination` raised `InputTooShort` for.
TOO_FEW_UNITS: list[tuple[str, str, dict[str, Any]]] = [
    ("boustrophedon", ONE_SENTENCE, {}),
    ("cent_mille_milliards", ONE_SENTENCE, {"seed": 0}),
    ("ideenwuerfeln", "only one line", {"seed": 0}),
    ("recombination", ONE_SENTENCE, {"seed": 0}),
    ("spoonerism", "solo", {}),
    ("wechselsatz", ONE_SENTENCE, {"seed": 0}),
]


@pytest.mark.parametrize(("pid", "text", "params"), TOO_FEW_UNITS)
def test_too_few_units_is_always_the_same_code(pid: str, text: str, params: dict[str, Any]) -> None:
    """A caller retrying on `input_too_short` must not have to know which name
    each procedure happened to pick for the identical refusal."""
    with pytest.raises(DenckringError) as caught:
        generator(pid).apply(text, **params)
    assert caught.value.code == "input_too_short"
    assert caught.value.to_dict()["detail"]["found"]


def test_adequate_input_still_works() -> None:
    """The guard must not have made these procedures unusable."""
    produced = generator("boustrophedon").apply("one two three\nfour five six\nseven eight\n")
    assert produced.strip() != "one two three\nfour five six\nseven eight"


def test_a_frame_that_offers_choices_is_never_told_it_offers_none() -> None:
    """The no-choice guard must count what the reader wrote, not what survived.

    `drawable` used to run first, so `'a|. b|.'` — two slots, two separators —
    was refused with "none with a choice" and told to add the separator it had
    already supplied twice. It now draws, and a frame that really is starved is
    refused by the guard that can name the alternative it could not use.
    """
    assert generator("wechselsatz").apply("a|. b|.", seed=1).split() == ["a", "b"]

    with pytest.raises(InputTooShort) as caught:
        generator("wechselsatz").apply("a|b .", seed=1)
    message = str(caught.value)
    assert "none with a choice" not in message
    assert "'.'" in message
