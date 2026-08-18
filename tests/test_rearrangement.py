"""The result holds exactly the source's parts, in an order a rule produced."""

from denckring import check, get
from denckring.core.protocol import Constructive

SOURCE = """the cat sat down
a dog ran fast
one bird flew high"""


def test_boustrophedon_reverses_alternate_lines() -> None:
    turned = "the cat sat down\ntsaf nar god a\none bird flew high"
    assert check("boustrophedon", turned, source=SOURCE).satisfied is True


def test_boustrophedon_rejects_an_unturned_line() -> None:
    report = check("boustrophedon", SOURCE, source=SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "line_not_turned" for v in report.violations)


def test_a_rearrangement_may_not_invent_material() -> None:
    added = "the cat sat down\ntsaf nar god a\none bird flew high\nand a new line"
    report = check("boustrophedon", added, source=SOURCE)
    assert report.satisfied is False


def test_boustrophedon_apply_round_trips() -> None:
    procedure = get("boustrophedon")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(SOURCE)
    assert produced
    report = procedure.check(produced, source=SOURCE)
    assert report.satisfied


def test_text_folding_brings_the_far_flap_forward() -> None:
    folded = "three\nfour\nfive\none\ntwo"
    source = "one\ntwo\nthree\nfour\nfive"
    assert check("text_folding", folded, source=source, fold_at=2).satisfied is True


def test_text_folding_rejects_the_unfolded_source() -> None:
    source = "one\ntwo\nthree\nfour\nfive"
    report = check("text_folding", source, source=source, fold_at=2)
    assert report.satisfied is False
    assert any(v.rule == "line_out_of_fold" for v in report.violations)


def test_text_folding_may_not_invent_material() -> None:
    source = "one\ntwo\nthree\nfour\nfive"
    added = "three\nfour\nfive\none\ntwo\nsix"
    report = check("text_folding", added, source=source, fold_at=2)
    assert report.satisfied is False


def test_text_folding_apply_round_trips() -> None:
    procedure = get("text_folding")
    assert isinstance(procedure, Constructive)
    source = "one\ntwo\nthree\nfour\nfive"
    produced = procedure.apply(source, fold_at=2)
    assert produced
    report = procedure.check(produced, source=source, fold_at=2)
    assert report.satisfied
