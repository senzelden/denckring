from denckring import check
from denckring.procedures.quenina import infer_size, is_valid_size, spiral


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


def _sestina(words: str = "abcdef") -> str:
    """A whole sestina's end-words: `size` stanzas, rotated by the spiral each time."""
    order = spiral(len(words))
    stanza = list(words)
    lines: list[str] = []
    for _ in range(len(words)):
        lines += stanza
        stanza = [stanza[index] for index in order]
    return "\n".join(lines)


def test_the_size_is_read_off_the_text_when_it_is_not_given() -> None:
    """`n` is optional, so the inference is the default path — and it is the path
    every golden case, strategy and test here used to skip by passing `n`."""
    assert infer_size(list("abcdef") + list("faebdc")) == 6
    assert infer_size(["x"]) == 1
    assert infer_size([]) == 0


def test_an_unparametrised_quenina_can_actually_fail() -> None:
    """The bug this replaced: the inference returned 1 for every text, so no stanza
    was ever compared against the rotation, `total` came back 0, and `_report`
    scored that 1.0 as vacuously satisfied. The row accepted everything put to it.
    """
    assert check("quenina", _sestina()).satisfied
    assert not check("quenina", "\n".join(list("abcdefghijklmnopqr"))).satisfied
    assert not check("quenina", "the cat\na dog\nthe bird").satisfied


def test_a_single_wrong_end_word_fails_without_n_as_it_does_with_it() -> None:
    """The case that shows the inference was hiding a working checker rather than a
    broken one: with `n=6` this always failed, and only the default path passed it.
    """
    broken = "\n".join([*_sestina().splitlines()[:35], "z"])
    assert not check("quenina", broken, n=6).satisfied
    assert not check("quenina", broken).satisfied
