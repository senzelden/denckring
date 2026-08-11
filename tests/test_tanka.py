from denckring import check

TANKA = """an old silent pond
a frog jumps into the pond
splash silence again
a frog jumps into the pond
a frog jumps into the pond"""


def test_a_five_line_tanka_is_satisfied() -> None:
    assert check("tanka", TANKA).satisfied


def test_a_haiku_is_not_a_tanka() -> None:
    assert not check(
        "tanka",
        """an old silent pond
a frog jumps into the pond
splash silence again""",
    ).satisfied
