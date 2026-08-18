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


#: The refrain: identical text at indices 7, 15, 23 and 27 — the four lettered
#: "c" positions the scheme shares with no other line.
BALLADE_REFRAIN = "until the northern wind has blown"

#: Three eight-line ababbcbc stanzas and a bcbc envoi. The scheme repeats its
#: three letters across all three stanzas rather than resetting per stanza, so
#: a genuine ballade needs the fourteen b-lines, the six a-lines and the four
#: non-refrain c-lines each on a distinct word within their own letter — every
#: one below is. Not adapted from OTTAVA or SPENSERIAN, since neither of those
#: uses the same rhyme sounds across stanzas the way a ballade must.
BALLADE_LINES = [
    "a cat can climb a tall old tree",  # 0 a
    "the dog will run and play all day",  # 1 b
    "the bird will fly out to the sea",  # 2 a
    "the sun will shine and light the way",  # 3 b
    "the sky will clear by first of may",  # 4 b
    "the wall was built of gray old stone",  # 5 c
    "the birds will call what they all say",  # 6 b
    BALLADE_REFRAIN,  # 7 c refrain
    "the clock will chime at half past three",  # 8 a
    "the boys will laugh and run to play",  # 9 b
    "a fish will leap and swim so free",  # 10 a
    "the guests will come and wish to stay",  # 11 b
    "the storm clouds turn both dark and gray",  # 12 b
    "the barn stood dark and stayed alone",  # 13 c
    "the goats will roam and love to stray",  # 14 b
    BALLADE_REFRAIN,  # 15 c refrain
    "he holds the door shut with a key",  # 16 a
    "the trees will bend then start to sway",  # 17 b
    "the priest will grant the poor his plea",  # 18 a
    "the child will shape the wet soft clay",  # 19 b
    "the light comes down in one long ray",  # 20 b
    "the truth at last to all was known",  # 21 c
    "the hens will rest then soon they lay",  # 22 b
    BALLADE_REFRAIN,  # 23 c refrain
    "the men will come at dusk to pay",  # 24 b
    "the corn stood tall for it had grown",  # 25 c
    "the ships will sail out past the bay",  # 26 b
    BALLADE_REFRAIN,  # 27 c refrain
]


def test_ballade_requires_the_refrain_to_repeat() -> None:
    """Three eight-line stanzas and a four-line envoi, every stanza ending alike."""
    text = "\n".join(BALLADE_LINES)
    assert check("ballade", text).satisfied is True
    broken = "\n".join([*BALLADE_LINES[:27], "a different closing line entirely"])
    report = check("ballade", broken)
    assert report.satisfied is False
    assert any(v.rule == "broken_refrain" for v in report.violations)


def test_ballade_rejects_an_accidental_rhyme_reuse() -> None:
    """Only the refrain may repeat a word. A non-refrain line stealing another
    line's rhyme word is not the refrain, and must still be flagged."""
    reused = list(BALLADE_LINES)
    # Line 9 already ends "play"; line 24 reusing it is not a refrain position.
    reused[24] = "the men will come at dusk to play"
    report = check("ballade", "\n".join(reused))
    assert report.satisfied is False
    assert any(v.rule == "identical_rhyme" for v in report.violations)
