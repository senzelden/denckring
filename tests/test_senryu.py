from denckring import check


def test_the_measure_matches_the_haiku() -> None:
    assert check(
        "senryu",
        """an old silent pond
a frog jumps into the pond
splash silence again""",
    ).satisfied


def test_a_wrong_measure_is_not_satisfied() -> None:
    assert not check("senryu", "an old silent pond\na frog jumps in\nsplash").satisfied
