"""A generator that returns its input has not run the procedure.

The round-trip property — `check(apply(text))` is satisfied — is passed
trivially by the identity, which is how a generator returning its own input
survived every gate this project runs.
"""

import pytest

from denckring.core.errors import DegenerateOutput
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def generator(pid: str) -> Constructive:
    """`get` is typed as the checking base, which has no `apply`."""
    procedure = get(pid)
    assert isinstance(procedure, Constructive)
    return procedure


def test_the_error_carries_what_a_caller_needs() -> None:
    error = DegenerateOutput("anagram")
    assert error.code == "degenerate_output"
    assert error.to_dict()["detail"]["procedure_id"] == "anagram"
    assert "allow_identity" in str(error)


def test_allow_identity_is_the_way_through() -> None:
    """`every_nth_word` with n=1 keeps every word, which is the honest identity
    and the reason the escape hatch exists."""
    produced = generator("every_nth_word").apply("one two three", n=1, allow_identity=True)
    assert produced.split() == ["one", "two", "three"]


def test_without_the_flag_that_same_call_is_refused() -> None:
    with pytest.raises(DegenerateOutput):
        generator("every_nth_word").apply("one two three", n=1)


def test_the_message_does_not_claim_the_procedure_never_ran() -> None:
    """The guard cannot tell a no-op from a draw that came up the identity.

    `recombination` shuffles two sentences and lands on the identity permutation
    for half of all seeds — seed 0 among them. The procedure ran; only the draw
    was unlucky. An error that said otherwise would be this guard committing the
    fault it exists to catch.
    """
    with pytest.raises(DegenerateOutput) as caught:
        generator("recombination").apply("One. Two.", seed=0)
    message = str(caught.value)
    assert "did not run" not in message
    assert "identical to its input" in message
    assert "allow_identity" in message
