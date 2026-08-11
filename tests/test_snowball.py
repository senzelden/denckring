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
