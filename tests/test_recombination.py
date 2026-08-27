import pytest

from denckring import check
from denckring.core.errors import DegenerateOutput
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def generator(pid: str) -> Constructive:
    """`get` is typed as the checking base, which has no `apply`."""
    procedure = get(pid)
    assert isinstance(procedure, Constructive)
    return procedure


def test_reordered_sentences_are_satisfied() -> None:
    assert check("recombination", "B. A.", source="A. B.").satisfied


def test_a_dropped_sentence_is_a_violation() -> None:
    report = check("recombination", "A.", source="A. B.")
    assert not report.satisfied
    assert any(v.rule == "sentence_dropped" for v in report.violations)


def test_an_invented_sentence_is_a_violation() -> None:
    report = check("recombination", "A. B. C.", source="A. B.")
    assert any(v.rule == "sentence_not_in_source" for v in report.violations)


def test_an_unterminated_trailing_fragment_stays_out_of_the_shuffle() -> None:
    """A real recombination, with an unterminated tail carried along unshuffled.

    `SENTENCE_SPLIT` only splits after a terminator, so `'A. B. tail'` tokenises
    as `['A.', 'B.', 'tail']` with `'tail'` carrying none. Before the fix, `tail`
    was eligible for the shuffle; when it landed anywhere but last, the join
    glued it onto its new neighbour into a token the same regex could not split
    back apart, and `check` rejected `apply`'s own output for it. Pinning the
    tail in final position keeps the two real sentences free to permute while
    the join stays invertible.
    """
    produced = generator("recombination").apply("A. B. tail", seed=1)
    assert produced == "B. A. tail"
    assert check("recombination", produced, source="A. B. tail").satisfied


def test_a_lone_terminator_and_an_unterminated_fragment_is_degenerate() -> None:
    """The case the bug was found on: `'. . a'` tokenises as `['.', '.', 'a']`.

    `'a'` is the unterminated tail and is pinned out of the shuffle, leaving two
    identical `'.'` tokens to permute — every permutation of which is the same
    string, so the call is refused as degenerate rather than producing text its
    own checker would have rejected.
    """
    with pytest.raises(DegenerateOutput):
        generator("recombination").apply(". . a", seed=0)
