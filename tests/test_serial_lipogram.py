import string

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def parts_without(letters: str) -> str:
    """One paragraph per letter, each omitting the letter it is assigned."""
    return "\n\n".join(
        " ".join(ch for ch in string.ascii_lowercase if ch != drop) for drop in letters
    )


def test_each_part_omitting_its_letter_is_satisfied() -> None:
    assert check("serial_lipogram", parts_without("abc")).satisfied


def test_a_part_keeping_its_letter_violates() -> None:
    report = check("serial_lipogram", "aaa\n\nbbb")
    assert not report.satisfied
    assert any(v.rule == "letter_present" for v in report.violations)


def test_the_walk_starts_at_a_by_default() -> None:
    """Unlike abecedarian, the start cannot be read off the text: a missing
    letter looks like any other letter a short part happens to lack."""
    report = check("serial_lipogram", "zzz")
    assert report.satisfied, "a part without 'a' satisfies the first constraint"


def test_start_moves_the_walk() -> None:
    report = check("serial_lipogram", "aaa", start="b")
    assert report.satisfied


def test_lines_can_be_the_unit() -> None:
    text = "\n".join(" ".join(c for c in string.ascii_lowercase if c != d) for d in "ab")
    assert check("serial_lipogram", text, unit="line").satisfied


def test_more_parts_than_the_alphabet_wraps() -> None:
    assert check("serial_lipogram", parts_without(string.ascii_lowercase + "a")).satisfied


def test_start_must_be_a_single_letter() -> None:
    with pytest.raises(InvalidParams):
        check("serial_lipogram", "x", start="ab")


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
