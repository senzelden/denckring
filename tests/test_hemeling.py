"""Hemeling: two constraints on one text, failing and reported independently."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams

GLOSS = "the letters of your name will turn and then\nthey say a truer thing than they did when"
BROKEN_RHYME = (
    "the letters of your name will turn and then\nthey say a truer thing than they did now"
)


def test_both_halves_holding_satisfies() -> None:
    report = check("hemeling", f"listen\n{GLOSS}", source="silent")
    assert report.satisfied
    assert report.metrics["gloss_lines"] == 2


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (f"listen\n{BROKEN_RHYME}", "does_not_rhyme"),
        (f"listens\n{GLOSS}", "surplus_letter"),
    ],
)
def test_either_half_can_fail_alone(text: str, rule: str) -> None:
    """The point of the row: a machine can judge both halves, so it can say which
    one broke. A single boolean over the pair could not."""
    report = check("hemeling", text, source="silent")
    assert not report.satisfied
    assert report.score == 0.5
    assert rule in {violation.rule for violation in report.violations}


def test_a_violation_points_at_the_line_it_is_on() -> None:
    """`multiset_violations` carries no offset, because `anagram` compares two
    whole texts; here the anagram is one line of several. And the gloss's own
    offsets are relative to the gloss, which starts one line in."""
    report = check("hemeling", f"listens\n{BROKEN_RHYME}", source="silent")
    offsets = {violation.rule: violation.offset for violation in report.violations}
    assert offsets["surplus_letter"] == 0
    assert offsets["does_not_rhyme"] is not None
    assert offsets["does_not_rhyme"] > len("listens")


def test_the_anagram_alone_is_not_a_hemeling() -> None:
    """Which is the whole reason this row is not `anagram` with extra steps."""
    report = check("hemeling", "listen", source="silent")
    assert [v.rule for v in report.violations] == ["wrong_line_count"]


def test_the_scheme_sets_how_many_lines_the_explication_has() -> None:
    quatrain = (
        "the letters of your name will turn and then\n"
        "they say a truer thing than they did now\n"
        "and what was hidden there is plain again\n"
        "as clear as any oath a man could vow"
    )
    assert check("hemeling", f"listen\n{quatrain}", source="silent", scheme="ABAB").satisfied
    assert not check("hemeling", f"listen\n{quatrain}", source="silent", scheme="AABB").satisfied


def test_a_scheme_with_no_letters_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("hemeling", f"listen\n{GLOSS}", source="silent", scheme="--")


def test_an_anagram_of_nothing_is_not_an_anagram() -> None:
    """A text with no letters has nothing surplus to report, so the multiset
    comparison alone cannot fail it. `anagram._check` refuses the same case."""
    report = check("hemeling", f".\n{GLOSS}", source="silent")
    assert "empty_anagram" in {violation.rule for violation in report.violations}


def test_german_runs_the_same_two_checks() -> None:
    text = (
        "Leben\nder Wandrer zieht durch jenes weite Land\ndas Feuer brennt und wärmt die kalte Hand"
    )
    report = check("hemeling", text, lang="de", source="Nebel")
    assert report.satisfied
