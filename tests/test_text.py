from denckring.core.text import letter_spans, line_identity, line_spans, word_spans
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


def test_paragraph_spans_splits_on_a_crlf_blank_line() -> None:
    """A blank line ending in \\r\\n closes a paragraph, same as line_spans."""
    from denckring.core.text import paragraph_spans

    text = "first\r\n\r\nsecond"
    spans = paragraph_spans(text)
    assert [t for _, t in spans] == ["first", "second"]


def test_paragraph_spans_offsets_are_always_exact() -> None:
    """Every returned offset points at the start of its own text, verbatim."""
    from denckring.core.text import paragraph_spans

    for text in (
        "first para\nstill first\n\nsecond para\n\n\nthird",
        "aaa\n\nbbb",
        "\n\n   \n",
        "first\r\n\r\nsecond",
        "  a \r\n\r\n b  \n\nc",
    ):
        for offset, part in paragraph_spans(text):
            assert text[offset : offset + len(part)] == part


def test_line_identity_ignores_only_the_line_s_final_punctuation() -> None:
    """A refrain returns with the punctuation its new syntax wants — Passerat's
    villanelle closes it `Tourterelle:`, then `Tourterelle.`, then `Tourterelle,`
    — so comparing raw lines reads a working refrain as broken."""
    assert line_identity("I'ay perdu ma Tourterelle:") == line_identity(
        "I'ay perdu ma Tourterelle."
    )
    assert line_identity("Le premier jour du mois de mai !") == line_identity(
        "Le premier jour du mois de mai"
    )


def test_line_identity_keeps_apostrophes_and_internal_punctuation() -> None:
    """French elision is part of the word, not decoration on the line: `l'âme`
    and `i'oy` must survive, and only the end of the line is variable."""
    assert line_identity("j'ai dans l'âme un chagrin amer :") == "j'ai dans l'âme un chagrin amer"
    assert line_identity("Eft-ce point celle que i'oy?") == "eft-ce point celle que i'oy"


def test_line_identity_still_separates_lines_differing_in_a_word() -> None:
    """The guard against over-permissiveness: this must not turn every refrain
    check into a formality."""
    assert line_identity("I'ay perdu ma Tourterelle.") != line_identity("I'ay perdu ma Colombe.")
