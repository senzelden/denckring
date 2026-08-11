from denckring import check


def test_deleting_the_letter_throughout_is_satisfied() -> None:
    assert check("slenderizing", "bat", source="brat", deleted="r").satisfied


def test_keeping_the_letter_is_a_violation() -> None:
    assert not check("slenderizing", "brat", source="brat", deleted="r").satisfied


def test_extra_letters_are_reported() -> None:
    report = check("slenderizing", "batx", source="brat", deleted="r")
    assert any(v.rule == "extra_letters" for v in report.violations)
