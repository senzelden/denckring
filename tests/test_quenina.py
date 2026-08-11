from denckring import check
from denckring.procedures.quenina import is_valid_size, spiral


def test_the_spiral_is_the_sestina_rotation() -> None:
    assert [i + 1 for i in spiral(6)] == [6, 1, 5, 2, 4, 3]


def test_valid_sizes_are_the_queneau_numbers() -> None:
    assert [n for n in range(1, 13) if is_valid_size(n)] == [1, 2, 3, 5, 6, 9, 11]


def test_a_correct_rotation_is_satisfied() -> None:
    lines = []
    for stanza in [["a", "b", "c"], ["c", "a", "b"], ["b", "c", "a"]]:
        lines += [f"x {w}" for w in stanza]
    assert check("quenina", "\n".join(lines), n=3).satisfied


def test_a_broken_rotation_is_not_satisfied() -> None:
    lines = []
    for stanza in [["a", "b", "c"], ["a", "b", "c"], ["a", "b", "c"]]:
        lines += [f"x {w}" for w in stanza]
    assert not check("quenina", "\n".join(lines), n=3).satisfied


def test_an_invalid_size_is_reported() -> None:
    report = check("quenina", "x a\nx b\nx c\nx d", n=4)
    assert any(v.rule == "invalid_size" for v in report.violations)
