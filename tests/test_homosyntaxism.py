"""Homosyntaxism: the source's tag sequence, with new content words.

Every text here is real English rather than generated letters, because the
verdict comes from a tagger and a tagger has nothing to say about `zzzz`.
"""

from denckring import check
from denckring.lang import get_pack
from denckring.procedures.homosyntaxism import tagged_tokens

SOURCE = "The boy ate the bread."


def test_the_same_structure_with_new_words_is_satisfied() -> None:
    report = check("homosyntaxism", "The girl read the book.", source=SOURCE)
    assert report.satisfied
    assert report.metrics["tokens"] == 5.0


def test_a_different_structure_is_a_violation() -> None:
    report = check("homosyntaxism", "Bread was eaten quickly.", source=SOURCE)
    assert not report.satisfied
    # `eaten` lands where `ate` was and is a VERB too, so position 2 passes:
    # the row is a positional correspondence, not a judgement about the whole
    # sentence, and a passive rewriting keeps one position by accident.
    assert [violation.rule for violation in report.violations] == [
        "wrong_pos",
        "wrong_pos",
        "wrong_pos",
        "missing_word",
    ]
    assert report.score == 0.2


def test_an_open_class_word_kept_from_the_source_is_a_violation() -> None:
    """The half of the definition a tag-only checker would silently drop."""
    report = check("homosyntaxism", "The girl ate the book.", source=SOURCE)
    assert not report.satisfied
    violation = report.violations[0]
    assert violation.rule == "repeated_word"
    assert violation.found == "ate"
    assert violation.expected == "a new VERB"


def test_a_closed_class_word_kept_from_the_source_is_not() -> None:
    """The ruling recorded in the module docstring, asserted rather than assumed.

    Both determiners and the preposition are the source's own words, and the
    row is satisfied anyway. If a later decision requires every word to be new,
    this is the test that must be changed to say so — which is the point of
    pinning the rule rather than only the passing case above.
    """
    report = check(
        "homosyntaxism", "The girl ran to the window.", source="The boy walked to the door."
    )
    assert report.satisfied
    assert not report.violations


def test_a_text_shorter_than_its_source_reports_each_unanswered_position() -> None:
    report = check("homosyntaxism", "The girl read.", source=SOURCE)
    assert not report.satisfied
    assert [violation.rule for violation in report.violations] == ["missing_word", "missing_word"]
    assert [violation.expected for violation in report.violations] == ["DET", "NOUN"]
    assert all(violation.offset is None for violation in report.violations)
    assert report.score == 0.6


def test_a_text_longer_than_its_source_reports_the_tail_once() -> None:
    report = check("homosyntaxism", "The girl read the book today.", source=SOURCE)
    assert not report.satisfied
    assert [violation.rule for violation in report.violations] == ["extra_words"]
    assert report.violations[0].found == "today"


def test_an_empty_source_is_not_vacuously_satisfied() -> None:
    """`max(len(expected), len(actual))` is what stops it, and the reason the
    denominator is not `len(expected)`: a source with no tokens would otherwise
    divide by zero words and score any text at all 1.0."""
    report = check("homosyntaxism", "The girl read the book.", source="")
    assert not report.satisfied
    assert report.score == 0.0
    assert report.violations[0].rule == "extra_words"


def test_an_empty_text_and_an_empty_source_are_vacuously_satisfied() -> None:
    """The rule `_report` documents and `letter_class_report` relies on: with
    nothing on either side there is no constraint left to fail."""
    assert check("homosyntaxism", "", source="").satisfied


def test_a_violation_on_an_unseen_form_says_so() -> None:
    report = check("homosyntaxism", "The girl pulled the cart.", source="The boy pushed the cart.")
    assert not report.satisfied
    violation = report.violations[0]
    assert violation.rule == "repeated_word"
    assert violation.found == "cart"
    assert violation.note is not None
    assert "never saw" in violation.note


def test_undecided_words_counts_positions_the_tagger_guessed_at() -> None:
    """Reported whether or not the position produced a violation: `cart` and
    `mat` are both absent from the training data, both tag NOUN, and the row is
    satisfied — a reader deciding how far to trust that needs the count.

    Counted per *position* and not per token, which is why two unseen forms
    facing each other are one undecided word: the verdict being qualified is
    the comparison, and there is one of those at each position.
    """
    report = check("homosyntaxism", "The girl pulled the mat.", source="The boy pushed the cart.")
    assert report.satisfied
    assert report.metrics["undecided_words"] == 1.0


def test_violation_offsets_point_into_the_whole_text() -> None:
    """Not into the sentence the token fell in. The offending verb is in the
    second sentence, so an offset rebased per sentence would be 12, not 36."""
    text = "The girl read the book. The teacher read the letter."
    report = check("homosyntaxism", text, source="The boy ate the bread. The man read the door.")
    assert not report.satisfied
    offset = report.violations[0].offset
    assert offset is not None
    assert text[offset:].startswith("read")
    assert offset == 36


def test_each_sentence_is_tagged_on_its_own() -> None:
    """Red-proofed against tagging the whole text in one call, which is what
    `pos_tags` warns degrades the answer: `fast` in `He runs fast.` is ADJ when
    its own sentence is tagged and ADP when the two sentences arrive as one bag
    of words.
    """
    pack = get_pack("en")
    text = "He runs fast. The morning runs were hard."
    per_sentence = [token.tag.upos for token in tagged_tokens(text, pack)]
    whole_text = [tag.upos for tag in pack.pos_tags(pack.tokenize(text))]
    assert per_sentence[2] == "ADJ"
    assert whole_text[2] == "ADP"
