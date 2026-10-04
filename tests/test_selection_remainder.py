"""Two more selections: one by column, one by line ending."""

from typing import Any

import pytest

from denckring import check, get
from denckring.core.protocol import Constructive

PAGE = """the cat sat down
a dog ran fast
one bird flew high"""


def test_column_reading_takes_the_nth_word_of_each_line() -> None:
    assert check("column_reading", "cat dog bird", source=PAGE, column=2).satisfied is True


def test_column_reading_rejects_the_wrong_column() -> None:
    report = check("column_reading", "cat dog bird", source=PAGE, column=1)
    assert report.satisfied is False


def test_column_reading_apply_round_trips() -> None:
    procedure = get("column_reading")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(PAGE, column=2)
    assert produced
    report = procedure.check(produced, source=PAGE, column=2)
    assert report.satisfied


def test_haikuization_keeps_the_line_ends() -> None:
    assert check("haikuization", "down fast high", source=PAGE).satisfied is True


def test_haikuization_rejects_a_word_that_was_not_a_line_end() -> None:
    """The rule is `wrong_line_end`, in the house `wrong_*` family. It read
    `not_a_line_end` while `column_reading`'s line-for-line identical block read
    `wrong_column_word`; both now come from `positional_report`, which takes the
    name as a parameter because the two rows genuinely name different things."""
    report = check("haikuization", "cat fast high", source=PAGE)
    assert report.satisfied is False
    assert any(v.rule == "wrong_line_end" for v in report.violations)


def test_column_reading_and_haikuization_share_one_positional_check() -> None:
    """Same shape, same tail: a word out of place, then one violation for the
    surplus. The two blocks were duplicated in full before `positional_report`.
    Aligned (ADR 0056), a tie puts the gap last, so the surplus is still the tail
    even on `haikuization`, where no word matches."""
    by_column = check("column_reading", "cat dog bird extra", source=PAGE, column=2)
    by_line_end = check("haikuization", "cat dog bird extra", source=PAGE)
    for report in (by_column, by_line_end):
        assert report.satisfied is False
        assert report.violations[-1].rule == "extra_words"
        assert report.violations[-1].found == "extra"


def test_haikuization_apply_round_trips() -> None:
    procedure = get("haikuization")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(PAGE)
    assert produced
    report = procedure.check(produced, source=PAGE)
    assert report.satisfied


def test_haikuization_tolerates_a_line_end_outside_the_dictionary() -> None:
    """R18: `haikuization` no longer requires `phonemes`, precisely so an
    invented word at a line's end produces a report rather than raising
    `MissingCapability` — the fragility that requiring `phonemes` bought with
    no corresponding benefit, since the rhyme machinery never distinguished a
    rhyme-word reading from a line-end one anyway."""
    source = "the sky is bright\na word made up: flurbish"
    report = check("haikuization", "bright flurbish", source=source)
    assert report.satisfied is True


# A word the text runs out before is placed at the end of the text, the
# convention `every_nth_word` and `slenderizing` share (`Violation.offset`).
@pytest.mark.parametrize(
    ("pid", "text", "params"),
    [("column_reading", "cat", {"column": 2}), ("haikuization", "down", {})],
)
def test_a_missing_tail_is_placed_at_the_end_of_the_text(
    pid: str, text: str, params: dict[str, Any]
) -> None:
    report = check(pid, text, source=PAGE, **params)
    missing = [v.offset for v in report.violations if v.found == ""]
    assert missing == [len(text), len(text)]


def test_column_reading_fails_source_words_appended_after_the_column() -> None:
    """R-F1: the column with source words appended is not the column. It used to pass
    beside its own `extra_words` violation, because the surplus never reached the
    denominator. `haikuization` shares `positional_report` but cannot reach that case:
    its last expected word is the source's last word, so any word appended after it is
    also `not_in_source`, which already failed the text."""
    report = check("column_reading", "cat dog bird high", source=PAGE, column=2)
    assert report.satisfied is False
    assert report.score < 1.0
    assert [v.rule for v in report.violations] == ["extra_words"]
    after_the_end = check("haikuization", "down fast high high", source=PAGE)
    assert {v.rule for v in after_the_end.violations} >= {"extra_words", "not_in_source"}
