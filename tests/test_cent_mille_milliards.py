from denckring import check

MACHINE = """Auf | Ab
Nacht | Tag
kommt | geht"""


def test_a_poem_the_machine_offers_is_satisfied() -> None:
    assert check("cent_mille_milliards", "Ab\nTag\ngeht", source=MACHINE).satisfied


def test_a_line_the_machine_does_not_offer_is_a_violation() -> None:
    report = check("cent_mille_milliards", "Ab\nMond\ngeht", source=MACHINE)
    assert not report.satisfied
    assert report.violations[0].rule == "line_not_offered"


def test_a_missing_line_is_a_violation() -> None:
    report = check("cent_mille_milliards", "Ab\nTag", source=MACHINE)
    assert any(v.rule == "missing_line" for v in report.violations)


def test_the_report_counts_the_combinations() -> None:
    report = check("cent_mille_milliards", "Ab\nTag\ngeht", source=MACHINE)
    assert report.metrics["combinations"] == 8.0
