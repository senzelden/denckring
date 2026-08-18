"""Three short forms: one shrunken sonnet, one syllabic, one deliberately loose."""

from denckring import check

CURTAL = """the fish will swim beneath the frozen lake
the cat can see the moon above the tree
the dog will run across the field today
the deer will wake before the morning break
a bird can fly around the house at three
the sun will set behind the hill in may
the moon will rise and fill the sky with light
the boat will drift below the open sea
the wind will move the grass and blow away
the stars will burn until the end of night
the birds will sing before the break of day"""

ENGLYN = """the summer evening settles by the bay
beside the quiet way
and the swallow calls the day
and the river hums today"""

CLERIHEW = """sir humphry davy
abominated gravy
he mixed his chemicals every night
and left the lab in the pale light"""


def test_curtal_sonnet_is_eleven_lines() -> None:
    assert check("curtal_sonnet", CURTAL).satisfied is True
    assert check("curtal_sonnet", "\n".join(CURTAL.splitlines()[:10])).satisfied is False


def test_englyn_counts_syllables_not_stresses() -> None:
    report = check("englyn", ENGLYN)
    assert "estimated_words" in report.metrics


def test_englyn_rejects_the_wrong_syllable_pattern() -> None:
    wrong = "\n".join(["a short first line", *ENGLYN.splitlines()[1:]])
    assert check("englyn", wrong).satisfied is False


def test_clerihew_checks_rhyme_and_says_nothing_about_metre() -> None:
    """Its metre is irregular on purpose; checking it would reject every real one."""
    assert check("clerihew", CLERIHEW).satisfied is True
    assert all("metre" not in v.rule for v in check("clerihew", CLERIHEW).violations)
