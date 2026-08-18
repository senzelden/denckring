"""Three stanzas that differ only in length, scheme and metre."""

from denckring import check

OTTAVA = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the owl will call across the dark at sea
the fox will hide beneath the fallen way
the mice will creep beside the ancient stone
the birds will sing before the day has flown"""

SPENSERIAN = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the birds will sing before the break of day
the fox will hide beneath the fallen stone
the mice will creep beside the ancient way
the owl will call across the dark alone
and now the birds will sing before the day has flown"""


def test_ottava_rima_accepts_abababcc() -> None:
    assert check("ottava_rima", OTTAVA).satisfied is True


def test_ottava_rima_rejects_the_wrong_line_count() -> None:
    report = check("ottava_rima", "\n".join(OTTAVA.splitlines()[:7]))
    assert report.satisfied is False
    assert any(v.rule == "wrong_line_count" for v in report.violations)


def test_spenserian_final_line_is_an_alexandrine() -> None:
    """Eight pentameters and a hexameter. A ninth pentameter is the classic error."""
    assert check("spenserian_stanza", SPENSERIAN).satisfied is True
    short_last = "\n".join([*SPENSERIAN.splitlines()[:8], "the rain will fall upon the moor"])
    assert check("spenserian_stanza", short_last).satisfied is False


#: Three eight-line ababbcbc stanzas and a bcbc envoi, on the same three rhymes
#: throughout and closing every part on the same refrain line — the ballade
#: itself, not adapted from OTTAVA or SPENSERIAN, since neither of those uses
#: the same rhyme sounds across stanzas the way a ballade must.
BALLADE_LINES = [
    "a cat can climb a tall old tree",
    "the dog will run and play all day",
    "the bird will fly out to the sea",
    "the sun will shine and light the way",
    "the wind will blow and clouds will sway",
    "the leaves will fall where they were sown",
    "the rain will fall and skies grow gray",
    "till all the fields to gold have grown",
    "a fish will leap and swim so free",
    "the stars will shine to mark the way",
    "the child will laugh and shout with glee",
    "the birds will sing and greet the day",
    "the waves will crash and touch the bay",
    "the fields lie still where seeds were sown",
    "the wind will call the ships to sway",
    "till all the fields to gold have grown",
    "the moon shines down on all the sea",
    "the sun goes down to end the day",
    "the fox runs fast and feels so free",
    "the birds fly south to find the bay",
    "the leaves will turn from green to gray",
    "the seeds lie deep where they were sown",
    "the birds will call to greet the day",
    "till all the fields to gold have grown",
    "the fields will wait the whole long day",
    "the seeds will wait till they have grown",
    "the fields will wait the whole long day",
    "till all the fields to gold have grown",
]


def test_ballade_requires_the_refrain_to_repeat() -> None:
    """Three eight-line stanzas and a four-line envoi, every stanza ending alike."""
    text = "\n".join(BALLADE_LINES)
    assert check("ballade", text).satisfied is True
    broken = "\n".join([*BALLADE_LINES[:27], "a different closing line entirely"])
    report = check("ballade", broken)
    assert report.satisfied is False
    assert any(v.rule == "broken_refrain" for v in report.violations)
