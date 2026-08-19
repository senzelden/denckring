"""Carroll's doublets: one letter per step, every step a word."""

from denckring import check
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def test_a_valid_ladder_is_accepted() -> None:
    assert check("word_ladder", "cold cord card ward warm").satisfied is True


def test_a_step_changing_two_letters_is_rejected() -> None:
    report = check("word_ladder", "cold card warm")
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "step_too_large")
    assert violation.found == "card"


def test_a_step_that_is_not_a_word_is_rejected() -> None:
    report = check("word_ladder", "cold cald card ward warm")
    assert report.satisfied is False
    assert any(v.rule == "not_a_word" for v in report.violations)


def test_apply_finds_a_ladder_its_own_check_accepts() -> None:
    """The round-trip property every generative row must satisfy."""
    procedure = get("word_ladder")
    assert isinstance(procedure, Constructive)
    ladder = procedure.apply("cold", target="warm")
    assert check("word_ladder", ladder).satisfied is True
    assert ladder.split()[0] == "cold"
    assert ladder.split()[-1] == "warm"
