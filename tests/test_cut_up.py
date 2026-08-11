from denckring import check, get
from denckring.core.protocol import Constructive

SOURCE = "the quick brown fox jumps"


def test_words_drawn_from_the_source_are_satisfied() -> None:
    assert check("cut_up", "fox the jumps", source=SOURCE).satisfied


def test_an_invented_word_is_a_violation() -> None:
    report = check("cut_up", "zebra", source=SOURCE)
    assert not report.satisfied
    assert report.violations[0].found == "zebra"


def test_reusing_a_word_more_often_than_the_source_has_it_is_a_violation() -> None:
    assert not check("cut_up", "the the", source=SOURCE).satisfied


def test_apply_is_deterministic_under_a_seed() -> None:
    procedure = get("cut_up")
    assert isinstance(procedure, Constructive)
    assert procedure.apply(SOURCE, seed=3) == procedure.apply(SOURCE, seed=3)
