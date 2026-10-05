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


# Every violation is placed, as `positional_report` places its siblings'. A word
# missing from the end of the text is placed at the end, where it would go.
def test_a_wrong_word_is_placed_at_the_text_word() -> None:
    report = check("every_nth_word", "two  five six eight", source=SOURCE, n=2)
    assert [(v.rule, v.offset, v.found) for v in report.violations] == [("wrong_word", 5, "five")]


def test_a_missing_tail_is_placed_at_the_end_of_the_text() -> None:
    report = check("every_nth_word", "two four", source=SOURCE, n=2)
    assert [(v.rule, v.offset) for v in report.violations] == [
        ("missing_word", 8),
        ("missing_word", 8),
    ]


def test_extra_words_are_placed_at_the_first_extra_word() -> None:
    report = check("every_nth_word", "two four six eight nine ten", source=SOURCE, n=2)
    assert [(v.rule, v.offset, v.found) for v in report.violations] == [
        ("extra_words", 19, "nine ten")
    ]
