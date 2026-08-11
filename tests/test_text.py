from denckring.core.text import letter_spans, line_spans, word_spans
from denckring.lang import get_pack

PACK = get_pack("en")


def test_letter_spans_fold_and_lowercase_and_carry_offsets() -> None:
    assert letter_spans("Éh!", PACK) == [(0, "e"), (1, "h")]


def test_letter_spans_ignore_digits_and_punctuation() -> None:
    assert letter_spans("a1 b.", PACK) == [(0, "a"), (3, "b")]


def test_word_spans_carry_offsets() -> None:
    assert word_spans("one two", PACK) == [(0, "one"), (4, "two")]


def test_line_spans_skip_blank_lines_and_carry_offsets() -> None:
    assert line_spans("a\n\n b \n") == [(0, "a"), (3, " b ")]
