from denckring import check


def test_interlocked_quatrains_are_satisfied() -> None:
    assert check("pantoum", "a\nb\nc\nd\nb\ne\nd\nf").satisfied


def test_a_broken_interlock_is_a_violation() -> None:
    report = check("pantoum", "a\nb\nc\nd\nz\ne\nd\nf")
    assert not report.satisfied
    assert report.violations[0].rule == "broken_interlock"


def test_a_single_quatrain_is_vacuously_satisfied() -> None:
    assert check("pantoum", "a\nb\nc\nd").satisfied
