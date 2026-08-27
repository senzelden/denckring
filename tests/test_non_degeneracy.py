"""A generator that returns its input has not run the procedure.

The round-trip property — `check(apply(text))` is satisfied — is passed
trivially by the identity, which is how a generator returning its own input
survived every gate this project runs.
"""

import pytest

from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DegenerateOutput
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures, get


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


#: The three generators whose `_apply` never reads `text`. Named `pid` rather
#: than `procedure_id` for the reason the other suites document: conftest's
#: `pytest_generate_tests` parametrises that name over the whole registry and
#: pytest errors on the duplicate.
IGNORES_INPUT = ["denckring", "llull_figure", "poesie_automat"]


@pytest.mark.parametrize("pid", IGNORES_INPUT)
def test_a_device_that_ignores_its_input_may_produce_it(pid: str) -> None:
    """The guard compared output against an argument these three never read.

    `denckring.apply("", seed=3)` spells `geRyffisch`; feeding that back under
    the same seed spells it again, because the rings do not know what they were
    handed. Refusing the second call — which is what the guard did — called a
    procedure that ran correctly degenerate, and did it in the explorer, whose
    generated page invites the reader to paste output back in.
    """
    produced = generator(pid).apply("", seed=3)
    assert produced.strip()
    assert generator(pid).apply(produced, seed=3) == produced


def test_only_those_three_opt_out() -> None:
    """The opt-out silences a real guard, so its membership is pinned.

    A generator that reads its text and adds `ignores_input` would lose the
    non-degeneracy check altogether rather than gain an exemption from a
    meaningless comparison.
    """
    opted_out = sorted(
        pid
        for pid, procedure in all_procedures().items()
        if isinstance(procedure, ConstructiveProcedure) and procedure.ignores_input
    )
    assert opted_out == IGNORES_INPUT
