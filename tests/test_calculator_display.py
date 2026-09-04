"""The seven-segment display, with no language in sight."""

from denckring.core.calculator import ALPHABET, FROM_DIGIT, from_digits, to_digits


def test_the_four_attested_words_decode() -> None:
    """Verified by decoding rather than by reading them off a web page.

    `illegible` is the sharpest: the form in circulation uses `9` for the `g`,
    and this row's own generator emits `6`. Both are correct (ADR 0037 D4).
    """
    assert from_digits("07734") == "hello"
    assert from_digits("5318008") == "boobies"
    assert from_digits("53177187714") == "hillbillies"
    assert from_digits("378193771") == "illegible"
    assert from_digits("378163771") == "illegible"


def test_esel_is_7353() -> None:
    assert to_digits("Esel") == "7353"
    assert from_digits("7353") == "esel"


def test_a_word_outside_the_alphabet_has_no_digits() -> None:
    assert to_digits("cat") is None
    assert to_digits("blessé") is None


def test_g_is_emitted_as_six_and_accepted_as_either() -> None:
    """`6` and `9` both rotate onto G, so `apply` is not the inverse of `check`
    for a word containing one — a third of every corpus. ADR 0037 D4 fixes the
    emitted spelling at `6`, because the practice's own name encodes g from 6."""
    assert to_digits("igel") == "7361"
    assert from_digits("7361") == "igel"
    assert from_digits("7391") == "igel"


def test_two_is_not_a_letter() -> None:
    """`2` is rotationally symmetric on a seven-segment display, so the folk
    `2 -> Z` is a pun on the printed digit rather than a property of the
    machine. ADR 0037 D2 refuses it, and `2 -> R` with it."""
    assert "2" not in FROM_DIGIT
    assert from_digits("2") == ""
    assert to_digits("zebra") is None


def test_the_alphabet_is_the_eight_letters_beghilos_names() -> None:
    assert sorted(ALPHABET) == sorted("beghilos")


def test_a_phrase_is_entered_last_word_first() -> None:
    """The machine is read from the other end, so the digits of the *last* word
    are entered first. Getting this backwards reads a two-word phrase in the
    wrong order, which is the bug this plan's own draft carried."""
    esel, hose = to_digits("esel"), to_digits("hose")
    assert esel is not None and hose is not None
    assert esel + hose == "73533504"
    assert from_digits("73533504") == "hoseesel"
