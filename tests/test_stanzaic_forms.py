"""Three stanzas that differ only in length, scheme and metre."""

import pytest

from denckring import check, prompt_hint
from denckring.core.errors import InvalidParams, UnsetHintParameter

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


#: The same ballade with two syllables in front of every line, refrain included:
#: iambic pentameter, the length White (1887) says real ballades also take.
BALLADE_PENTAMETER = ["and so " + line for line in BALLADE_LINES]


def test_ballade_default_metre_is_the_tetrameter_it_always_checked() -> None:
    """`metre` at its default judges exactly as the row did before it existed."""
    for lines in (BALLADE_LINES, BALLADE_PENTAMETER):
        text = "\n".join(lines)
        assert check("ballade", text) == check("ballade", text, metre="01" * 4)


def test_ballade_metre_names_the_line_the_checker_scans() -> None:
    """A pentameter ballade fails the default on length, and passes `metre` of ten."""
    text = "\n".join(BALLADE_PENTAMETER)
    default = check("ballade", text)
    assert default.satisfied is False
    assert {v.rule for v in default.violations} == {"wrong_line_length"}
    assert check("ballade", text, metre="01" * 5).satisfied is True
    tetrameter = check("ballade", "\n".join(BALLADE_LINES), metre="01" * 5)
    assert {v.rule for v in tetrameter.violations} == {"wrong_line_length"}


def test_ballade_without_a_metre_still_checks_rhyme_and_refrain() -> None:
    """`metre=None` drops the line scan alone; line count, rhyme and refrain stand."""
    assert check("ballade", "\n".join(BALLADE_PENTAMETER), metre=None).satisfied is True
    short = check("ballade", "\n".join(BALLADE_PENTAMETER[:27]), metre=None)
    assert {v.rule for v in short.violations} == {"wrong_line_count"}
    broken = [*BALLADE_PENTAMETER[:27], "and so until the southern wind has blown"]
    assert {v.rule for v in check("ballade", "\n".join(broken), metre=None).violations} == {
        "broken_refrain"
    }
    reused = list(BALLADE_PENTAMETER)
    reused[24] = "and so the men will come at dusk to play"
    rules = {v.rule for v in check("ballade", "\n".join(reused), metre=None).violations}
    assert rules == {"identical_rhyme"}


@pytest.mark.parametrize("metre", ["", "0101x101", "iambic"])
def test_ballade_refuses_a_metre_that_is_not_a_stress_pattern(metre: str) -> None:
    with pytest.raises(InvalidParams):
        check("ballade", "\n".join(BALLADE_LINES), metre=metre)


def test_ballade_hint_states_the_metre_it_will_be_judged_on() -> None:
    """The hint asks for the pattern set, never for the tetrameter regardless."""
    pentameter = prompt_hint("ballade", metre="01" * 5)
    assert "0101010101" in pentameter
    assert "tetrameter" not in pentameter and "eight syllables" not in pentameter
    assert "01010101" in prompt_hint("ballade")


def test_ballade_hint_without_a_metre_is_refused_rather_than_invented() -> None:
    """`metre=None` leaves no line to ask for, so the hint names the gap."""
    with pytest.raises(UnsetHintParameter) as raised:
        prompt_hint("ballade", metre=None)
    assert "metre" in str(raised.value)
