"""The calculator word: check, then apply."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_esel_satisfies_7353_in_german() -> None:
    report = check("calculator_word", "Esel", lang="de", digits="7353")
    assert report.satisfied
    assert report.score == 1.0


def test_the_wrong_digits_are_a_violation_naming_both_readings() -> None:
    report = check("calculator_word", "Esel", lang="de", digits="7354")
    assert not report.satisfied
    wrong = [v for v in report.violations if v.rule == "wrong_digits"]
    assert len(wrong) == 1
    assert wrong[0].found == "7353"
    assert wrong[0].expected == "7354"


def test_a_letter_the_display_cannot_write_is_located() -> None:
    report = check("calculator_word", "cat", lang="en", digits="743")
    assert not report.satisfied
    bad = [v for v in report.violations if v.rule == "undisplayable_letter"]
    assert [v.found for v in bad] == ["c", "a", "t"]
    assert [v.offset for v in bad] == [0, 1, 2]


def test_an_undisplayable_text_is_not_also_blamed_for_its_digits() -> None:
    """One cause, one violation. A text the display cannot write has no digit
    reading to compare, so reporting `wrong_digits` too would name two faults
    for one fact and send a caller to fix the wrong thing first."""
    report = check("calculator_word", "cat", lang="en", digits="743")
    assert "wrong_digits" not in [v.rule for v in report.violations]


def test_a_displayable_non_word_fails_on_the_lexicon() -> None:
    report = check("calculator_word", "hlose", lang="en", digits="35074")
    assert not report.satisfied
    assert "not_a_word" in [v.rule for v in report.violations]


def test_require_words_false_checks_the_mapping_alone() -> None:
    """The "combinations" reading: the display must be able to write it, and the
    lexicon is not consulted."""
    report = check("calculator_word", "hlose", lang="en", digits="35074", require_words=False)
    assert report.satisfied


def test_the_word_count_is_checked() -> None:
    report = check("calculator_word", "Hose Esel", lang="de", digits="73533504", words=1)
    assert not report.satisfied
    assert "wrong_word_count" in [v.rule for v in report.violations]


def test_a_two_word_phrase_reads_last_word_first() -> None:
    """The machine is read from the other end, so `Hose Esel` is entered as
    `to_digits("esel") + to_digits("hose")`. Reversing that reads the phrase
    backwards, which is the bug the plan's own draft carried."""
    assert check("calculator_word", "Hose Esel", lang="de", digits="73533504", words=2).satisfied


def test_either_digit_spelling_of_g_is_accepted() -> None:
    """`6` and `9` both rotate onto G (ADR 0037 D4), so both spellings of a word
    containing one must satisfy the same text."""
    for digits in ("7361", "7391"):
        assert check("calculator_word", "Igel", lang="de", digits=digits).satisfied


def test_an_accented_word_is_not_a_calculator_word_by_default() -> None:
    """The row's fold default is FALSE, inverting every other row (ADR 0037 D3):
    a calculator cannot write `blessé`, it writes `BLESSE`."""
    report = check("calculator_word", "blessé", lang="fr", digits="355378")
    assert not report.satisfied
    assert "undisplayable_letter" in [v.rule for v in report.violations]


def test_folding_can_be_asked_for_explicitly() -> None:
    """The lenient reading stays reachable; only the default changed."""
    report = check("calculator_word", "blessé", lang="fr", digits="355378", fold_diacritics=True)
    assert report.satisfied


def test_the_german_sharp_s_is_undisplayable_by_default() -> None:
    """`Geheiß` shows as GEHEISS. Under folding it would be accepted, which is
    false about the machine — the other half of D3."""
    assert not check("calculator_word", "Geheiß", lang="de", digits="5513436").satisfied


def test_the_sharp_s_is_accepted_under_explicit_folding() -> None:
    assert check(
        "calculator_word", "Geheiß", lang="de", digits="5513436", fold_diacritics=True
    ).satisfied


def test_digits_containing_two_are_refused() -> None:
    """`2` maps to no letter (D2), so a `digits` value containing one cannot
    describe any text: malformed input rather than a failed check."""
    with pytest.raises(InvalidParams):
        check("calculator_word", "Esel", lang="de", digits="7253")


def test_digits_must_be_digits() -> None:
    with pytest.raises(InvalidParams):
        check("calculator_word", "Esel", lang="de", digits="73a3")


def test_an_empty_text_is_not_vacuously_satisfied() -> None:
    """`_report` enforces `satisfied == (score == 1.0)`, and a whole-text fault
    marked by flagging "every word" marks nothing when there are no words. An
    empty text scored 1.0 while carrying two violations — a satisfied report
    with complaints attached, the shape ADR 0035 fixed in `lipogram`."""
    for text in ("", "   "):
        report = check("calculator_word", text, lang="de", digits="7353")
        assert not report.satisfied, repr(text)
        assert report.violations
