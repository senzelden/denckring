import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_a_closed_walk_without_repeated_edges_is_satisfied() -> None:
    assert check("eodermdrome", "eodermdrome").satisfied


def test_an_open_walk_is_a_violation() -> None:
    report = check("eodermdrome", "abc")
    assert not report.satisfied
    assert any(v.rule == "not_closed" for v in report.violations)


def test_a_repeated_edge_is_a_violation() -> None:
    report = check("eodermdrome", "ababa")
    assert any(v.rule == "repeated_edge" for v in report.violations)


def test_a_single_letter_is_too_short() -> None:
    assert not check("eodermdrome", "a").satisfied


def test_a_short_word_passes_unless_a_minimum_is_asked_for() -> None:
    """A9: `dead` passed. The default minimum is still two letters."""
    assert check("eodermdrome", "dead").satisfied
    report = check("eodermdrome", "dead", min_letters=7)
    assert not report.satisfied
    assert report.score == 0.0
    [violation] = report.violations
    assert (violation.rule, violation.expected) == ("too_short", "at least 7 letters")
    assert check("eodermdrome", "eodermdrome", min_letters=11).satisfied


def test_the_default_minimum_reads_as_it_always_has() -> None:
    assert check("eodermdrome", "a").violations[0].expected == "at least two letters"


def test_a_minimum_below_two_is_refused() -> None:
    with pytest.raises(InvalidParams, match="greater than or equal to 2"):
        check("eodermdrome", "a", min_letters=1)
