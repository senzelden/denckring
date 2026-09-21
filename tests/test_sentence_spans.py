"""`sentence_spans`, the unit the `pos` rows tag in — ADR 0045.

The helper exists because the two splitters already here answer different
questions, and reaching for the nearest-looking one was a real defect on this
branch: `_TERMINAL_PUNCTUATION`'s comment says "sentence punctuation" while the
constant carries `,;:`. These tests pin the distinction so it cannot quietly
collapse back.
"""

from __future__ import annotations

from denckring.core.text import clause_spans, sentence_spans


def test_a_comma_does_not_end_a_sentence() -> None:
    """The whole reason this helper exists rather than a reuse.

    Measured over ten comma-heavy texts, clause-splitting changes three verdicts
    and is wrong in all three — it reports a finite verb in *The lamps, unlit,
    above the empty road*, which has none. Apposition set off by commas is the
    characteristic shape of verbless prose.
    """
    text = "The lamps, unlit, above the empty road."
    assert [piece for _, piece in sentence_spans(text)] == [text]


def test_a_semicolon_and_a_colon_do_not_end_a_sentence_either() -> None:
    text = "Horses, scarcely better; splashed to their very blinkers."
    assert [piece for _, piece in sentence_spans(text)] == [text]


def test_it_differs_from_clause_spans_on_exactly_that() -> None:
    """Both helpers stay, and neither may absorb the other. Asserted as a
    difference rather than by pinning `clause_spans`' own output, which is that
    helper's business."""
    text = "Fog everywhere, fog up the river."
    assert len(clause_spans(text)) == 2
    assert len(sentence_spans(text)) == 1


def test_a_full_stop_question_mark_exclamation_and_ellipsis_all_end_one() -> None:
    text = "Night. Morning? Evening! Then nothing… and the road."
    assert [piece for _, piece in sentence_spans(text)] == [
        "Night.",
        "Morning?",
        "Evening!",
        "Then nothing…",
        "and the road.",
    ]


def test_offsets_point_into_the_original_text() -> None:
    """A violation must be clickable in the text the caller passed, so the spans
    must not be offsets into a slice. This is the property that makes the
    grouping worth doing over `word_spans` rather than over sliced strings."""
    text = "Night.  Morning."
    spans = sentence_spans(text)
    assert spans == [(0, "Night."), (8, "Morning.")]
    for offset, piece in spans:
        assert text[offset : offset + len(piece)] == piece


def test_a_trailing_sentence_with_no_final_stop_is_not_lost() -> None:
    """Prose ends mid-sentence more often than not — a fragment, a caption, a
    line of verse. Dropping it would silently stop checking the last clause."""
    assert sentence_spans("Night. The long road") == [(0, "Night."), (7, "The long road")]


def test_an_empty_or_blank_text_has_no_sentences() -> None:
    assert sentence_spans("") == []
    assert sentence_spans("   \n  ") == []


def test_runs_of_punctuation_do_not_produce_empty_sentences() -> None:
    """`...` and `!?` are one boundary written emphatically, not three."""
    assert [piece for _, piece in sentence_spans("Night... Morning!?")] == [
        "Night.",
        "Morning!",
    ]


def test_an_abbreviation_ends_a_sentence_which_is_the_stated_cost() -> None:
    """Not a bug to be fixed quietly: the docstring says so, and telling `Mr.`
    from a full stop needs a lexicon this module does not have. Pinned so the
    limit is visible rather than discovered.
    """
    assert len(sentence_spans("Mr. Tulkinghorn is out.")) == 2
