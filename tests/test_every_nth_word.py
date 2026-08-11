from denckring import check, get
from denckring.core.protocol import Constructive

SOURCE = "one two three four five six seven eight"


def test_the_selection_is_satisfied() -> None:
    assert check("every_nth_word", "two four six eight", source=SOURCE, n=2).satisfied


def test_a_wrong_selection_is_not_satisfied() -> None:
    assert not check("every_nth_word", "one three five", source=SOURCE, n=2).satisfied


def test_apply_produces_what_check_accepts() -> None:
    procedure = get("every_nth_word")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(SOURCE, n=3)
    assert procedure.check(produced, source=SOURCE, n=3).satisfied
