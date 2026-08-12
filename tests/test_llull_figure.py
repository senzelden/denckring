"""Llull's ternary Ars: nine principles, read at six levels."""

import pytest

from denckring import check, get
from denckring.core import device as devices
from denckring.core.errors import UnknownFigure, UnknownLevel
from denckring.core.protocol import Constructive

FIGURE = devices.load_figure("llull_ternary")


def test_the_alphabet_is_nine_letters_and_skips_j() -> None:
    assert FIGURE.letters == list("BCDEFGHIK")
    assert "J" not in FIGURE.letters


def test_the_chamber_counts_are_computed_not_quoted() -> None:
    """84 ternary chambers and 36 pairs fall out of nine letters."""
    from math import comb

    assert len(FIGURE.chambers(3)) == comb(9, 3) == 84
    assert len(FIGURE.chambers(2)) == comb(9, 2) == 36


def test_the_same_letters_read_differently_at_each_level() -> None:
    """The multiple assignment is the device, not a convenience."""
    assert FIGURE.read("BCD", "absolute") == ["Bonitas", "Magnitudo", "Aeternitas"]
    assert FIGURE.read("BCD", "relative") == ["Differentia", "Concordantia", "Contrarietas"]
    assert FIGURE.read("BCD", "questions") == ["Utrum", "Quid", "De quo"]


def test_every_level_names_all_nine_letters() -> None:
    for level in FIGURE.level_names():
        assert set(FIGURE.levels[level]) == set(FIGURE.letters), level


def test_a_chamber_written_as_letters_is_satisfied() -> None:
    assert check("llull_figure", "BCD").satisfied
    assert check("llull_figure", "B C D").satisfied


def test_a_chamber_spelled_out_is_satisfied_at_any_level() -> None:
    assert check("llull_figure", "Bonitas Magnitudo Aeternitas").satisfied
    assert check("llull_figure", "Differentia Concordantia Contrarietas").satisfied


def test_naming_the_wrong_level_is_not_satisfied() -> None:
    assert not check("llull_figure", "Bonitas Magnitudo Aeternitas", level="relative").satisfied


def test_a_repeated_principle_is_a_violation() -> None:
    report = check("llull_figure", "BB")
    assert any(v.rule == "repeated_principle" for v in report.violations)


def test_the_wrong_number_of_principles_is_a_violation() -> None:
    assert any(v.rule == "wrong_arity" for v in check("llull_figure", "BC").violations)
    assert check("llull_figure", "BC", arity=2).satisfied


def test_something_that_is_not_a_principle_at_all() -> None:
    report = check("llull_figure", "Bonitas Magnitudo Zebra")
    assert report.violations[0].rule == "not_a_chamber"


def test_turning_the_wheels_produces_a_chamber_the_figure_accepts() -> None:
    procedure = get("llull_figure")
    assert isinstance(procedure, Constructive)
    for seed in range(8):
        assert check("llull_figure", procedure.apply("", seed=seed)).satisfied


def test_kirchers_figure_is_the_same_mechanism_with_different_stock() -> None:
    kircher = devices.load_figure("kircher_ars_magna")
    assert len(kircher.chambers(3)) == 84
    assert kircher.read("BCD", "absolute") == ["Bonitas", "Magnitudo", "Duratio"]


def test_an_unknown_figure_names_what_is_available() -> None:
    with pytest.raises(UnknownFigure, match="llull_ternary"):
        devices.load_figure("no_such_figure")


def test_an_unknown_level_names_the_ones_that_exist() -> None:
    with pytest.raises(UnknownLevel, match="absolute"):
        FIGURE.read("BCD", "nonesuch")
