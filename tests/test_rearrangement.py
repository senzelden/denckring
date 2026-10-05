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


# A turned line is read as an unturned one is: stripped and casefolded, the
# policy `rearrangement_report` applies to every line. Compared byte for byte, a
# trailing space on a turned line was `line_not_turned` while the same space on
# an unturned line passed.
def test_boustrophedon_strips_a_turned_line_as_it_strips_the_others() -> None:
    for turned in (
        "the cat sat down\ntsaf nar god a \none bird flew high",
        "the cat sat down\n  tsaf nar god a\none bird flew high",
        "the cat sat down \ntsaf nar god a\none bird flew high",
    ):
        report = check("boustrophedon", turned, source=SOURCE)
        assert report.satisfied is True, (turned, report.violations)
        assert report.score == 1.0


def test_boustrophedon_casefolds_a_turned_line_as_it_casefolds_the_others() -> None:
    for turned in (
        "The cat sat down\ntsaf nar god a\none bird flew high",
        "the cat sat down\ntsaf nar god A\none bird flew high",
    ):
        assert check("boustrophedon", turned, source=SOURCE).satisfied is True, turned


def test_boustrophedon_still_rejects_a_padded_unturned_line() -> None:
    report = check(
        "boustrophedon", "the cat sat down\n a dog ran fast \none bird flew high", source=SOURCE
    )
    assert report.satisfied is False
    assert "line_not_turned" in {v.rule for v in report.violations}


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


# A2's one policy, held by the sibling row: a positional line is compared
# stripped and casefolded, as `rearrangement_report` compares every line.
def test_text_folding_strips_and_casefolds_a_folded_line() -> None:
    source = "one\ntwo\nthree\nfour\nfive"
    for folded in (
        "three \nfour\nfive\none\ntwo",
        "three\n  four\nfive\none\ntwo",
        "Three\nfour\nfive\none\nTWO",
    ):
        report = check("text_folding", folded, source=source, fold_at=2)
        assert report.satisfied is True, (folded, report.violations)


def test_text_folding_still_rejects_a_padded_unfolded_line() -> None:
    source = "one\ntwo\nthree\nfour\nfive"
    report = check("text_folding", " One\ntwo\nthree\nfour\nfive", source=source, fold_at=2)
    assert "line_out_of_fold" in {v.rule for v in report.violations}


def test_text_folding_apply_round_trips() -> None:
    procedure = get("text_folding")
    assert isinstance(procedure, Constructive)
    source = "one\ntwo\nthree\nfour\nfive"
    produced = procedure.apply(source, fold_at=2)
    assert produced
    report = procedure.check(produced, source=source, fold_at=2)
    assert report.satisfied
