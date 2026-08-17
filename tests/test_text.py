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


def test_paragraph_spans_splits_on_blank_lines() -> None:
    from denckring.core.text import paragraph_spans

    text = "first para\nstill first\n\nsecond para\n\n\nthird"
    spans = paragraph_spans(text)
    assert [t for _, t in spans] == ["first para\nstill first", "second para", "third"]


def test_paragraph_spans_keep_their_offsets() -> None:
    from denckring.core.text import paragraph_spans

    text = "aaa\n\nbbb"
    spans = paragraph_spans(text)
    assert spans[1][0] == text.index("bbb")


def test_paragraph_spans_of_a_blank_text_is_empty() -> None:
    from denckring.core.text import paragraph_spans

    assert paragraph_spans("\n\n   \n") == []
