"""The generic sonnet: fourteen lines, in whatever scheme the caller names."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams

SHAKESPEAREAN = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the fox will hide beneath the fallen stone
the fish will swim beneath the frozen lake
the owl will call across the dark alone
the deer will wake before the morning break
the moon will rise and fill the sky with light
the horse will stand beside the gate so still
the stars will burn until the end of night
the mouse will hide behind the open till
the clock will mark the passing of the time
the bell will ring and slowly start to chime"""


def test_fourteen_lines_in_the_named_scheme() -> None:
    report = check("sonnet", SHAKESPEAREAN, scheme="ABABCDCDEFEFGG", metre="01" * 5)
    assert report.satisfied is True


def test_thirteen_lines_is_not_a_sonnet() -> None:
    thirteen = "\n".join(SHAKESPEAREAN.splitlines()[:13])
    report = check("sonnet", thirteen, scheme="ABABCDCDEFEFGG", metre="01" * 5)
    assert report.satisfied is False
    assert len([v for v in report.violations if v.rule == "wrong_line_count"]) == 1


def test_the_line_count_violation_says_what_it_wanted() -> None:
    thirteen = "\n".join(SHAKESPEAREAN.splitlines()[:13])
    report = check("sonnet", thirteen, scheme="ABABCDCDEFEFGG", metre="01" * 5)
    violation = next(v for v in report.violations if v.rule == "wrong_line_count")
    assert violation.found == "13 lines"
    assert violation.expected == "14 lines"


def test_a_scheme_of_the_wrong_length_is_rejected_not_ignored() -> None:
    """A 12-letter scheme cannot describe a sonnet; accepting it would check nothing."""
    with pytest.raises(InvalidParams):
        check("sonnet", SHAKESPEAREAN, scheme="ABABCDCDEFEF", metre="01" * 5)
