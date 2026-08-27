"""A generator that returns its input, or nothing, has not run the procedure.

The round-trip property — `check(apply(text))` is satisfied — is passed
trivially by the identity, which is how a generator returning its own input
survived every gate this project runs. It is passed just as trivially by the
empty string, because `_report` scores an empty text 1.0; that is the same
defect and is refused by the same guard under the same error.
"""

import pytest

from denckring import check
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


def test_an_empty_result_is_refused_too() -> None:
    """`melting_text` drops words by coin, and on this text and seed it drops
    all of them. Returning `""` is the same defect as returning the input: the
    text says nothing about what the procedure did."""
    with pytest.raises(DegenerateOutput) as caught:
        generator("melting_text").apply("hello", seed=0)
    assert "empty" in str(caught.value)
    assert "allow_identity" in str(caught.value)


def test_the_empty_result_the_guard_refuses_would_otherwise_pass_every_gate() -> None:
    """Why the empty half belongs in the guard rather than in each generator.

    `_report` scores an empty text 1.0 — vacuously satisfied, as its own
    docstring says — so nothing downstream of `apply` could catch this. The
    round-trip property would have read a generator that returned nothing as a
    row that passed.
    """
    assert check("melting_text", "", source="hello").satisfied


def test_a_selection_that_selects_nothing_is_refused() -> None:
    """The second row that could do it: `every_nth_word` with a stride longer
    than the text selects no word at all."""
    with pytest.raises(DegenerateOutput):
        generator("every_nth_word").apply("one two", n=3)


def test_allow_identity_is_the_way_through_the_empty_case_as_well() -> None:
    """One escape for both shapes, because a caller cannot act differently on
    them — the same argument that gives them one error code."""
    assert generator("every_nth_word").apply("one two", n=3, allow_identity=True) == ""


def test_the_two_shapes_are_distinguishable_without_parsing_english() -> None:
    """One code, but `detail()` still says which was seen — a stable string a
    caller reads instead of the message."""
    identical = DegenerateOutput("anagram").to_dict()["detail"]["observed"]
    empty = DegenerateOutput("anagram", DegenerateOutput.EMPTY).to_dict()["detail"]["observed"]
    assert identical != empty
