from denckring import check


def test_a_rearrangement_is_satisfied() -> None:
    assert check("antigram", "silent", source="listen").satisfied


def test_the_source_itself_is_not_an_antigram() -> None:
    report = check("antigram", "listen", source="listen")
    assert not report.satisfied
    assert any(v.rule == "unchanged" for v in report.violations)
