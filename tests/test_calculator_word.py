"""The calculator word: check, then apply."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Lang


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


def test_apply_decodes_the_digits_to_a_word() -> None:
    from denckring import apply

    assert apply("calculator_word", "7353", lang="de").lower() == "esel"


def test_produce_partitions_into_the_requested_number_of_words() -> None:
    from denckring import produce

    production = produce("calculator_word", "73533504", lang="de", words=2)
    assert production.texts
    for text in production.texts:
        assert len(text.split()) == 2


def test_a_partition_that_cannot_be_made_raises_rather_than_returning_junk() -> None:
    from denckring import produce
    from denckring.core.errors import NoCandidateWord

    with pytest.raises(NoCandidateWord):
        produce("calculator_word", "73533504", lang="de", words=1)


def test_what_the_generator_makes_satisfies_its_own_checker() -> None:
    """The project's thesis, on this row, in all three languages."""
    from denckring import apply

    cases: list[tuple[Lang, str]] = [("en", "07734"), ("de", "7353"), ("fr", "713705")]
    for lang, digits in cases:
        text = apply("calculator_word", digits, lang=lang)
        assert check("calculator_word", text, lang=lang, digits=digits).satisfied, lang


def test_the_generator_emits_six_for_g_where_the_attested_form_uses_nine() -> None:
    """ADR 0037 D4, and the asymmetry it creates. The circulating ILLEGIBLE is
    378193771; this generator's own spelling of the same word is 378163771.
    Both decode correctly, and a reader assuming one canonical spelling will
    read the other as a bug."""
    from denckring import apply
    from denckring.core.calculator import to_digits

    assert to_digits("illegible") == "378163771"
    assert apply("calculator_word", "378193771", lang="en").lower() == "illegible"


def test_a_two_word_production_reads_in_the_order_the_display_shows() -> None:
    """The partition must be reversed before decoding: entering to_digits("esel")
    then to_digits("hose") and turning the machine over reads "hose esel"."""
    from denckring import produce

    texts = [t.lower() for t in produce("calculator_word", "73533504", lang="de", words=2).texts]
    assert "hose esel" in texts
