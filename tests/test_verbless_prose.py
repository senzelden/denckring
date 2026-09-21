"""verbless_prose: the finite-verb bar, and the honesty it has to carry with it."""

from denckring import check
from denckring.core.registry import get
from denckring.lang import get_pack
from denckring.procedures.verbless_prose import sentence_groups

# Bleak House (1853), chapter 1. Real verbless prose, which is why it is here:
# a constructed noun phrase proves only that the checker agrees with whoever
# wrote it.
BLEAK_HOUSE = (
    "London. Michaelmas term lately over, and the Lord Chancellor sitting in "
    "Lincoln's Inn Hall. Implacable November weather."
)


def test_verbless_prose_is_satisfied() -> None:
    assert check("verbless_prose", BLEAK_HOUSE).satisfied


def test_a_finite_verb_is_a_violation() -> None:
    report = check("verbless_prose", "She walked home through the rain.")
    assert not report.satisfied
    assert [violation.rule for violation in report.violations] == ["finite_verb"]
    assert report.violations[0].found == "walked"


def test_the_violation_points_into_the_whole_text_not_into_its_sentence() -> None:
    """Offsets are the caller's text's, even for a verb in a later sentence.

    The checker tags sentence by sentence, so this is the property that fails if
    a rewrite ever slices the text and tags the slices: the offset would come
    back rebased to its own sentence and still look plausible.
    """
    text = "Implacable November weather. Then the fog lifted."
    report = check("verbless_prose", text)
    offset = report.violations[0].offset
    assert offset is not None
    assert text[offset : offset + len("lifted")] == "lifted"


def test_a_participle_is_not_a_finite_verb() -> None:
    """The distinction the row exists for, and the reason `pos` had to be a tagger.

    `sitting` and `lowering` are verbs; barring them would bar the material the
    form is written out of.
    """
    report = check("verbless_prose", "Smoke lowering down from the chimney-pots.")
    assert [violation.found for violation in report.violations] != ["lowering"]
    tags = get_pack("en").pos_tags(["Smoke", "lowering", "down", "from", "the", "chimney"])
    assert tags[1].verb_form == "Part" or tags[1].verb_form == "Ger"


def test_a_word_is_read_in_its_sentence_and_not_alone() -> None:
    """`records` is a noun in one sentence and a finite verb in the other.

    The whole argument for `pos` being a tagger rather than a lookup (ADR 0045):
    no reading of the word on its own decides between them. ADR 0045 uses `walks`
    to make the point, and the shipped tagger does not in fact get that pair
    right — it reads `walks` as finite in *the evening walks* too — so the pair
    asserted here is one that was measured rather than the one that was written.
    """
    assert check("verbless_prose", "Her records of the year.").satisfied
    assert not check("verbless_prose", "She records the year.").satisfied


def test_the_report_counts_words_and_undecided_words() -> None:
    report = check("verbless_prose", "Implacable November weather.")
    assert report.metrics["words"] == 3.0
    assert report.metrics["undecided_words"] >= 0.0


def test_a_violation_on_an_unseen_form_says_so() -> None:
    """The honesty ADR 0045 requires: a verdict on a form the tagger never saw.

    `splashed` is absent from UD English-EWT, and Dickens's clause around it is
    verbless — so this violation is a false positive *and* one the reader is told
    not to trust. Both halves are the point.
    """
    report = check("verbless_prose", "Horses, scarcely better; splashed to their very blinkers.")
    violation = next(v for v in report.violations if v.found == "splashed")
    assert violation.note == "tagged from a form the tagger never saw in training"
    assert report.metrics["undecided_words"] >= 1.0


def test_a_violation_on_a_known_form_carries_no_note() -> None:
    """The note has to distinguish, or it says nothing."""
    report = check("verbless_prose", "She walked home.")
    assert report.violations[0].note is None


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("verbless_prose", "").satisfied


def test_the_row_ships_no_generator() -> None:
    """`kind: restrictive`: ADR 0002 makes `apply` optional and this row declines it."""
    assert not hasattr(get("verbless_prose"), "apply")


def test_sentences_are_grouped_on_the_punctuation_core_text_defines() -> None:
    """A group per sentence, with the whole text's offsets kept.

    Asserted as the rule rather than as today's grouping of one sample: every
    word appears exactly once, in order, at an offset that still indexes the
    text it came from.
    """
    text = "London. Michaelmas term over; fog everywhere."
    groups = sentence_groups(text, get_pack("en"))
    assert len(groups) > 1
    flat = [span for group in groups for span in group]
    assert [word for _, word in flat] == [word for _, word in get_pack("en").word_spans(text)]
    assert all(text[offset : offset + len(word)] == word for offset, word in flat)
