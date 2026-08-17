import string

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def parts_without(letters: str) -> str:
    """One paragraph per letter, each omitting the letter it is assigned."""
    return "\n\n".join(
        " ".join(ch for ch in string.ascii_lowercase if ch != drop) for drop in letters
    )


def lines_without(letters: str) -> str:
    """One line per letter, each omitting the letter it is assigned."""
    return "\n".join(
        " ".join(ch for ch in string.ascii_lowercase if ch != drop) for drop in letters
    )


def test_a_full_alphabets_worth_of_parts_each_omitting_its_letter_is_satisfied() -> None:
    assert check("serial_lipogram", parts_without(string.ascii_lowercase)).satisfied


def test_a_part_keeping_its_letter_violates() -> None:
    report = check("serial_lipogram", "aaa\n\nbbb")
    assert not report.satisfied
    assert any(v.rule == "letter_present" for v in report.violations)


def test_too_few_parts_violates_even_when_every_present_part_is_correct() -> None:
    """The form is 'as many parts as the alphabet has letters' — three correct
    parts is not the whole alphabet, so the text is genuinely incomplete."""
    report = check("serial_lipogram", parts_without("abc"))
    assert not report.satisfied
    assert any(v.rule == "wrong_part_count" for v in report.violations)
    assert not any(v.rule == "letter_present" for v in report.violations)


def test_empty_text_is_unsatisfied_not_vacuous() -> None:
    """An empty text has no parts at all, which is the wrong count, not a
    vacuous pass — unlike the restrictive procedures that forbid something
    an empty text trivially avoids."""
    report = check("serial_lipogram", "")
    assert not report.satisfied
    assert report.score == 0.0
    assert [v.rule for v in report.violations] == ["wrong_part_count"]


def test_the_walk_starts_at_a_by_default() -> None:
    """Unlike abecedarian, the start cannot be read off the text: a missing
    letter looks like any other letter a short part happens to lack."""
    report = check("serial_lipogram", "zzz")
    assert not any(v.rule == "letter_present" for v in report.violations)


def test_start_moves_the_walk() -> None:
    report = check("serial_lipogram", "aaa", start="b")
    assert not any(v.rule == "letter_present" for v in report.violations)


def test_lines_can_be_the_unit() -> None:
    text = lines_without(string.ascii_lowercase)
    assert check("serial_lipogram", text, unit="line").satisfied


def test_wraparound_avoids_letter_present_violations_beyond_the_alphabet() -> None:
    """More parts than letters wraps the walk back to the start; the extra
    part is still checked against the wrapped letter and gets it right, so
    the only violation left is the part count itself."""
    report = check("serial_lipogram", parts_without(string.ascii_lowercase + "a"))
    assert not report.satisfied
    assert all(v.rule == "wrong_part_count" for v in report.violations)


def test_start_must_be_a_single_letter() -> None:
    with pytest.raises(InvalidParams):
        check("serial_lipogram", "x", start="ab")


def test_start_outside_the_alphabet_is_invalid() -> None:
    with pytest.raises(InvalidParams):
        check("serial_lipogram", "x", start="ä")


def test_violation_in_the_second_paragraph_has_a_correctly_rebased_offset() -> None:
    """The bug in belle_absente: letter_spans is called on a part substring,
    so its offsets are relative to that part and must be added to the part's
    own offset within the full text. Prove it with a violation that is NOT in
    the first paragraph."""
    text = "bcdefghijklmnopqrstuvwxyz\n\nabcdefghijklmnopqrstuvwxyz"
    report = check("serial_lipogram", text)
    assert not report.satisfied
    violation = next(v for v in report.violations if v.rule == "letter_present")
    assert violation.offset is not None
    assert violation.offset > text.index("\n\n")
    assert text[violation.offset] == violation.found == "b"
