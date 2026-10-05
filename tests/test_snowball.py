from denckring import check

BORGMANN = "I do not know where family doctors acquired illegibly perplexing handwriting"


def test_borgmann_rhopalic_is_satisfied() -> None:
    assert check("snowball", BORGMANN).satisfied


def test_a_wrong_length_word_is_a_violation() -> None:
    report = check("snowball", "I do nope know")
    assert not report.satisfied
    assert report.violations[0].found == "nope"
    assert report.violations[0].expected == "3 letters"


def test_start_length_can_be_forced() -> None:
    assert check("snowball", "ab abc abcd", start=2).satisfied
    assert not check("snowball", "ab abc abcd", start=1).satisfied


def test_single_word_is_satisfied() -> None:
    assert check("snowball", "word").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("snowball", "").satisfied


# A word's length is its letters (ADR 0058, audit A10). The word pattern keeps an
# apostrophe between letters inside a word, and `len` counted it, so `I'm` was three.


def test_an_apostrophe_is_no_letter_of_the_word_it_sits_in() -> None:
    assert check("snowball", "A I'm the").satisfied
    report = check("snowball", "be I'm")
    assert [(v.found, v.expected) for v in report.violations] == [("I'm", "3 letters")]
    assert check("snowball", "I’m the", start=2).satisfied  # noqa: RUF001
    assert check("reverse_snowball", "the I'm a").satisfied


def test_a_hyphenated_compound_is_two_words_each_counted_by_its_letters() -> None:
    """The hyphen reading is unchanged and stated (`reading.word_examples`): a hyphen
    splits a word, so `well-known` is a four-letter word and then a five."""
    assert check("snowball", "I am the well-known").satisfied
    report = check("snowball", "I am the well-known man")
    assert [(v.found, v.expected) for v in report.violations] == [("man", "6 letters")]
    assert not check("snowball", "I am the self-made").satisfied
