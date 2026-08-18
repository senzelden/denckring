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
