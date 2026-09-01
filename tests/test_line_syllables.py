"""The line seam, and that adding it changed nothing for English or German."""

from denckring.lang import get_pack
from denckring.lang.base import BasePack
from denckring.procedures.syllable_count import line_syllables

FIXTURE = "the cat sat on the mat and thought of the wild mice\nthe dog ran home"


def test_the_default_is_the_per_word_sum() -> None:
    """English and German inherit today's behaviour by construction, which is
    the point of putting the default on the pack rather than in the procedure."""
    pack = get_pack("en")
    for line in FIXTURE.splitlines():
        expected = [pack.syllable_count(w) for w in pack.tokenize(line)]
        assert pack.line_syllables(line) == (
            sum(c for c, _ in expected),
            sum(1 for _, exact in expected if not exact),
        )


def test_english_and_german_line_counts_are_unchanged() -> None:
    """Asserted rather than assumed: this function is shared by five rows in
    three languages, and the seam exists to change exactly one of them.

    Whole-branch review Finding 6: the name promised both languages and only
    English ever appeared. German is unchanged by construction --
    `type(get_pack('de')).line_syllables is BasePack.line_syllables`, i.e.
    `GermanPack`/`GermanDataPack` override neither `syllables()`'s data path
    nor `line_syllables` itself -- but "unchanged by construction" is exactly
    the kind of claim this project measures rather than assumes (see D1's own
    test for English)."""
    assert line_syllables(FIXTURE, get_pack("en")) == [(0, 12, 0), (52, 4, 0)]
    assert type(get_pack("de")).line_syllables is BasePack.line_syllables
    assert line_syllables(
        "der Wind zieht durch das Land und trägt den Schnee davon", get_pack("de")
    ) == [(0, 12, 0)]


def test_a_pack_may_answer_for_a_whole_line() -> None:
    """The question `how long is this line` is asked of the thing that knows
    the language -- the move ADR 0030 made for `is_vowel_phoneme` after
    `assonance_constraint` answered it with CMUdict's convention."""

    from denckring.lang.en import EnglishPack

    class Counting(EnglishPack):
        """A pack that answers for the line rather than summing its words."""

        def line_syllables(self, line: str) -> tuple[int, int]:
            return (99, 1)

    assert line_syllables("anything at all", Counting()) == [(0, 99, 1)]
