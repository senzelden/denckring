"""Double dactyl — two quatrains, one line a single six-syllable word."""

from denckring import check
from denckring.procedures.double_dactyl import PATTERNS


def test_the_stanza_is_eight_lines() -> None:
    assert len(PATTERNS) == 8


def test_a_stanza_without_a_single_double_dactylic_word_is_rejected() -> None:
    """The one clause of the definition that is mechanically checkable."""
    text = "\n".join(
        ["higgledy piggledy"] * 3
        + ["carefully song"]
        + ["higgledy piggledy"] * 3
        + ["carefully song"]
    )
    report = check("double_dactyl", text)
    assert "no_double_dactylic_word" in [v.rule for v in report.violations]


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("double_dactyl", "")
    assert not report.satisfied
    assert report.violations
