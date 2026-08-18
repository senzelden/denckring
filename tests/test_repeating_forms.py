"""Two forms whose repeating element is a fragment, not a line."""

from denckring import check

RONDEAU = """the summer holds the door
the tiles lie warm upon the floor
a single swallow crosses sky
no one can say the reason why
the garden waits for something more
the bread is kept inside the store
the boats are drawn along the shore
a distant gull begins to cry
the summer holds
the thunder starts its far off roar
the candle burns an hour before
the wind goes past with one long sigh
the truth is not one to deny
the harvest time will soon restore
the summer holds"""

GHAZAL = """i cannot find the road tonight
the lamps have all been slowed tonight
the river takes another turn
and leaves its heavy load tonight
the letters that i never sent
are lying in the code tonight"""


def test_rondeau_accepts_the_rentrement() -> None:
    report = check("rondeau", RONDEAU, rentrement_words=3)
    assert report.satisfied is True


def test_rondeau_rejects_a_changed_rentrement() -> None:
    broken = RONDEAU.replace(
        "the boats are drawn along the shore\na distant gull begins to cry\nthe summer holds\n",
        "the boats are drawn along the shore\na distant gull begins to cry\nthe winter holds\n",
    )
    report = check("rondeau", broken, rentrement_words=3)
    assert report.satisfied is False
    assert any(v.rule == "broken_rentrement" for v in report.violations)


def test_ghazal_requires_the_radif_on_every_second_line() -> None:
    assert check("ghazal", GHAZAL).satisfied is True


def test_ghazal_names_the_line_that_drops_the_radif() -> None:
    broken = GHAZAL.replace("in the code tonight", "in the code today")
    report = check("ghazal", broken)
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "missing_radif")
    assert violation.expected == "tonight"


def test_ghazal_checks_the_rhyme_before_the_radif() -> None:
    broken = GHAZAL.replace("been slowed tonight", "been painted tonight")
    report = check("ghazal", broken)
    assert any(v.rule == "broken_qafia" for v in report.violations)
