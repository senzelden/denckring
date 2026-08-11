from denckring import check


def test_a_closed_walk_without_repeated_edges_is_satisfied() -> None:
    assert check("eodermdrome", "eodermdrome").satisfied


def test_an_open_walk_is_a_violation() -> None:
    report = check("eodermdrome", "abc")
    assert not report.satisfied
    assert any(v.rule == "not_closed" for v in report.violations)


def test_a_repeated_edge_is_a_violation() -> None:
    report = check("eodermdrome", "ababa")
    assert any(v.rule == "repeated_edge" for v in report.violations)


def test_a_single_letter_is_too_short() -> None:
    assert not check("eodermdrome", "a").satisfied
