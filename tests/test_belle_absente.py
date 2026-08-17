import pytest

from denckring import check
from denckring.core.errors import InvalidParams

# Every letter except the one each line omits. Built by hand so the test does
# not depend on the checker it is testing.
WITHOUT_A = "Blitz crwth vug jynx fed komp qophs"
WITHOUT_B = "Quartz glyph vex jocks fund whimp"


def test_a_line_per_letter_of_the_name() -> None:
    report = check("belle_absente", f"{WITHOUT_A}\n{WITHOUT_B}", name="ab")
    assert report.satisfied


def test_a_line_containing_its_own_letter_violates() -> None:
    report = check("belle_absente", "banana\nbanana", name="ab")
    assert not report.satisfied
    assert any(v.rule == "forbidden_letter" for v in report.violations)


def test_a_line_missing_another_letter_violates() -> None:
    report = check("belle_absente", "bcd\nacd", name="ab")
    assert not report.satisfied
    assert any(v.rule == "missing_letter" for v in report.violations)


def test_wrong_line_count_is_reported() -> None:
    report = check("belle_absente", WITHOUT_A, name="ab")
    assert any(v.rule == "wrong_line_count" for v in report.violations)


def test_the_name_reduces_to_its_letters() -> None:
    """`Georges Perec` is twelve constraints, not thirteen — the space is not one."""
    report = check("belle_absente", "x", name="Georges Perec")
    expected = [v for v in report.violations if v.rule == "wrong_line_count"]
    assert expected and "12" in expected[0].expected


def test_a_repeated_letter_is_a_repeated_constraint() -> None:
    """Perec's dedications repeat letters; each occurrence is its own line."""
    report = check("belle_absente", "x\nx\nx", name="aba")
    assert report.metrics["expected_lines"] == 3.0


def test_an_empty_name_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("belle_absente", "anything", name="!!!")


def test_violations_carry_offsets() -> None:
    # The offending line is the second one, so a line-relative offset (0)
    # would be indistinguishable from a correct text-relative offset here.
    text = "x\nbanana"
    report = check("belle_absente", text, name="ab")
    offending = [v for v in report.violations if v.rule == "forbidden_letter"]
    assert offending
    offset = offending[0].offset
    assert offset is not None
    assert text[offset] == "b"
