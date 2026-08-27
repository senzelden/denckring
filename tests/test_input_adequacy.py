"""Say what the input lacked, rather than handing it back unchanged.

Four generators returned their input when it could not feed them. That is
indistinguishable from a procedure that ran and changed nothing, which is why
the caller could not tell and neither could the eval.
"""

from typing import Any

import pytest

from denckring.core.errors import InputTooShort
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
