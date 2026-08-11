from denckring import check
from denckring.core import catalogue


def test_text_without_ascenders_or_descenders_is_satisfied() -> None:
    assert check("prisoners_constraint", "no one can see us or an oar").satisfied


def test_an_ascender_is_a_violation() -> None:
    report = check("prisoners_constraint", "a lone man")
    assert not report.satisfied
    assert report.violations[0].found == "l"


def test_a_descender_is_a_violation() -> None:
    assert not check("prisoners_constraint", "a page").satisfied


def test_capability_is_declared_in_the_catalogue() -> None:
    assert "letter_shapes" in catalogue.get("prisoners_constraint").requires


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("prisoners_constraint", "").satisfied
