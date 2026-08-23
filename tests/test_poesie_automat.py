"""Enzensberger's flap-board, and the line grouping the Device model grew for it."""

import pytest

from denckring import check, get
from denckring.core import device as devices
from denckring.core.protocol import Constructive

BOARD = devices.load("poesieautomat_2000")
RINGS = devices.load("harsdoerffer_1651")

PROCEDURE = get("poesie_automat")


def spun(seed: int) -> str:
    procedure = get("poesie_automat")
    assert isinstance(procedure, Constructive)
    return procedure.apply("", lang="de", seed=seed)


# ── the board ──────────────────────────────────────────────────────────────


def test_the_board_is_six_lines_of_six_modules_of_ten() -> None:
    assert BOARD.lines == [0, 1, 2, 3, 4, 5]
    assert [len(BOARD.for_line(n).slots) for n in BOARD.lines] == [6, 6, 6, 6, 6, 6]
    assert {len(slot.alternatives) for slot in BOARD.slots} == {10}


def test_the_board_gives_its_own_product() -> None:
    """10^36, computed from the modules rather than quoted from the literature.

    `combinations` is an `int` and stays one — the figure is 37 digits long and
    no float holds it exactly, which is why `metrics["combinations"]` is only
    ever the nearest float to it.
    """
    assert BOARD.combinations == 10**36
    assert len(str(BOARD.combinations)) == 37


def test_no_filler_is_shared_between_two_modules() -> None:
    """Ten per module is what makes the count a product of thirty-six tens.

    Compared case-folded, because that is how `segment` and `Slot.matches`
    compare: two modules differing only in a capital would be one flap twice.
    """
    fillers = [alternative.casefold() for slot in BOARD.slots for alternative in slot.alternatives]
    assert len(fillers) == 360
    assert len(set(fillers)) == 360


def test_flaps_are_whole_words_separated_by_single_spaces() -> None:
    """`_first_module_that_fails` asks the first *k* modules to spell a *word*
    prefix of the line, which is only the right question if no module boundary
    can ever fall inside a word."""
    for slot in BOARD.slots:
        for alternative in slot.alternatives:
            assert alternative == alternative.strip(), repr(alternative)
            assert " ".join(alternative.split()) == alternative, repr(alternative)
            assert alternative, f"{slot.name} carries an empty flap"


# ── check ──────────────────────────────────────────────────────────────────


def test_a_poem_off_the_board_is_one_the_board_admits() -> None:
    for seed in range(16):
        poem = spun(seed)
        assert check("poesie_automat", poem, lang="de").satisfied, poem


def test_spinning_is_deterministic_under_a_seed() -> None:
    assert spun(5) == spun(5)
    assert spun(5) != spun(6)


def test_a_word_on_no_flap_names_its_module_and_its_line() -> None:
    poem = spun(0).splitlines()
    poem[2] = poem[2].replace("knistert", "explodiert")
    report = check("poesie_automat", "\n".join(poem), lang="de")
    assert not report.satisfied
    assert len(report.violations) == 1
    violation = report.violations[0]
    assert violation.rule == "module_not_on_the_board"
    assert "module 2 (Verb) of line 3" in violation.expected


def test_a_line_the_board_can_show_in_another_row_is_still_refused() -> None:
    """The modules are per line. A line 5 the board shows in row five is not a
    line 1, which is what makes the count 10^36 and not 10^6."""
    lines = spun(0).splitlines()
    lines[0], lines[4] = lines[4], lines[0]
    report = check("poesie_automat", "\n".join(lines), lang="de")
    assert not report.satisfied
    assert {v.rule for v in report.violations} == {"module_not_on_the_board"}
    assert report.score == pytest.approx(4 / 6)


def test_a_missing_line_is_reported_rather_than_ignored() -> None:
    report = check("poesie_automat", "\n".join(spun(0).splitlines()[:4]), lang="de")
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["missing_line", "missing_line"]


def test_a_seventh_line_is_an_extra_line() -> None:
    poem = spun(0)
    report = check("poesie_automat", poem + "\n" + poem.splitlines()[0], lang="de")
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["extra_line"]


def test_whitespace_between_flaps_is_normalised() -> None:
    poem = spun(0).replace(" ", "   ")
    assert check("poesie_automat", poem, lang="de").satisfied


def test_the_metrics_carry_the_module_and_combination_counts() -> None:
    report = check("poesie_automat", spun(0), lang="de")
    assert report.metrics["modules"] == 36.0
    assert report.metrics["lines"] == 6.0
    assert report.metrics["combinations"] == float(10**36)


def test_nonsense_is_not_on_the_board() -> None:
    assert not check(
        "poesie_automat", "xyzzy\nxyzzy\nxyzzy\nxyzzy\nxyzzy\nxyzzy", lang="de"
    ).satisfied


# ── the Device change is additive ──────────────────────────────────────────


def test_a_device_that_never_mentions_a_line_reads_as_one_line() -> None:
    """Harsdörffer's file is untouched and must stay a flat, single-line device."""
    assert all(slot.line == 0 for slot in RINGS.slots)
    assert RINGS.lines == [0]
    assert RINGS.for_line(0).slots == RINGS.slots
    assert RINGS.for_line(0).combinations == RINGS.combinations


def test_segment_without_a_separator_is_what_it_always_was() -> None:
    assert devices.segment("verlangen", RINGS) == ["ver", "L", "a", "ng", "en"]
    assert devices.segment("verlangen", RINGS, separator="") == ["ver", "L", "a", "ng", "en"]


def test_a_separator_is_expected_between_pieces_and_only_between_them() -> None:
    board = BOARD.for_line(0)
    line = spun(0).splitlines()[0]
    assert devices.segment(line, board, separator=" ") is not None
    # The same words run together spell nothing: the walk wants its spaces.
    assert devices.segment(line.replace(" ", ""), board, separator=" ") is None
