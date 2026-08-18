"""The last two rows of the rearrangement cluster: fold_in, mathews_algorithm."""

from denckring import check, get
from denckring.core.protocol import Constructive

FOLD_SOURCE = "alpha beta gamma delta\nfive six seven\n\none two three four\neight nine ten"

TABLE_SOURCE = "the quick brown\n\nover lazy dogs\n\nsleep under warm"


def test_fold_in_joins_page_ones_left_half_to_page_twos_right_half() -> None:
    folded = "alpha beta three four\nfive six ten"
    assert check("fold_in", folded, source=FOLD_SOURCE).satisfied is True


def test_fold_in_rejects_page_one_read_unfolded() -> None:
    report = check("fold_in", "alpha beta gamma delta\nfive six seven", source=FOLD_SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "not_the_fold" for v in report.violations)


def test_fold_in_penalises_invented_material() -> None:
    folded = "alpha beta three four\nfive six ten"
    added = folded + "\nextra words here"
    report = check("fold_in", added, source=FOLD_SOURCE)
    assert report.satisfied is False
    assert report.score < 1.0


def test_fold_in_apply_round_trips() -> None:
    procedure = get("fold_in")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(FOLD_SOURCE)
    assert produced
    report = procedure.check(produced, source=FOLD_SOURCE)
    assert report.satisfied


def test_mathews_algorithm_rotates_each_row_by_its_index() -> None:
    read_across = "the quick brown\nlazy dogs over\nwarm sleep under"
    assert check("mathews_algorithm", read_across, source=TABLE_SOURCE).satisfied is True


def test_mathews_algorithm_rejects_the_table_read_unrotated() -> None:
    unrotated = "the quick brown\nover lazy dogs\nsleep under warm"
    report = check("mathews_algorithm", unrotated, source=TABLE_SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "word_out_of_rotation" for v in report.violations)


def test_mathews_algorithm_may_not_invent_material() -> None:
    read_across = "the quick brown\nlazy dogs over\nwarm sleep under"
    added = read_across + " extraword"
    report = check("mathews_algorithm", added, source=TABLE_SOURCE)
    assert report.satisfied is False
    assert report.score < 1.0


def test_mathews_algorithm_apply_round_trips() -> None:
    procedure = get("mathews_algorithm")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(TABLE_SOURCE)
    assert produced
    report = procedure.check(produced, source=TABLE_SOURCE)
    assert report.satisfied
