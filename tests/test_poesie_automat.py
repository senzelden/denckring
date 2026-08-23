"""Enzensberger's flap-board, and the line grouping the Device model grew for it."""

import re

import pytest

from denckring import check, get
from denckring.core import device as devices
from denckring.core.device import Device, Slot
from denckring.core.protocol import Constructive
from denckring.eval import harness

BOARD = devices.load("poesieautomat_2000")
RINGS = devices.load("harsdoerffer_1651")

PROCEDURE = get("poesie_automat")


def spun(seed: int) -> str:
    procedure = get("poesie_automat")
    assert isinstance(procedure, Constructive)
    return procedure.apply("", lang="de", seed=seed)


def flap_indices(poem: str) -> list[int]:
    """One flap index per module, read back off a poem the board admits.

    The inverse of `apply`, and the only way to say anything about *which* flaps
    a text shows rather than merely that it is on the board.
    """
    indices: list[int] = []
    for number, line in zip(BOARD.lines, poem.splitlines(), strict=True):
        board = BOARD.for_line(number)
        pieces = devices.segment(" ".join(line.split()), board, separator=" ")
        assert pieces is not None, f"line {number + 1} is not on the board: {line!r}"
        indices.extend(
            slot.alternatives.index(piece) for slot, piece in zip(board.slots, pieces, strict=True)
        )
    return indices


# ── the board ──────────────────────────────────────────────────────────────


def test_the_board_is_six_lines_of_six_modules_of_ten() -> None:
    assert BOARD.lines == [0, 1, 2, 3, 4, 5]
    assert [len(BOARD.for_line(n).slots) for n in BOARD.lines] == [6, 6, 6, 6, 6, 6]
    assert {len(slot.alternatives) for slot in BOARD.slots} == {10}


def test_the_board_gives_its_own_product() -> None:
    """10^36, computed from the modules rather than quoted from the literature.

    `combinations` is an `int` and stays one — the figure is 37 digits long and
    no float holds it exactly, which is why `metrics["combinations"]` is only
    ever the nearest float to it.
    """
    assert BOARD.combinations == 10**36
    assert len(str(BOARD.combinations)) == 37


def test_no_filler_is_shared_between_two_modules() -> None:
    """Ten per module is what makes the count a product of thirty-six tens.

    Compared case-folded, because that is how `segment` and `Slot.matches`
    compare: two modules differing only in a capital would be one flap twice.
    """
    fillers = [alternative.casefold() for slot in BOARD.slots for alternative in slot.alternatives]
    assert len(fillers) == 360
    assert len(set(fillers)) == 360


def test_flaps_are_whole_words_separated_by_single_spaces() -> None:
    """`_first_module_that_fails` asks the first *k* modules to spell a *word*
    prefix of the line, which is only the right question if no module boundary
    can ever fall inside a word."""
    for slot in BOARD.slots:
        for alternative in slot.alternatives:
            assert alternative == alternative.strip(), repr(alternative)
            assert " ".join(alternative.split()) == alternative, repr(alternative)
            assert alternative, f"{slot.name} carries an empty flap"


#: The board renders letter by letter into character cells, so a line costs six
#: flaps plus the five spaces between them. Eleven is the cap the lexicon was
#: written to; 71 is what six of them plus five spaces come to, and it is the
#: width the showcase board is built for.
FLAP_CAP = 11
BOARD_COLUMNS = 71


def test_no_flap_is_wider_than_the_board() -> None:
    """The defect this pins is a line that overflows the board.

    Both halves matter and neither implies the other: a flap longer than the cap
    is unshowable on its own, and six flaps that each fit can still assemble a
    line wider than the board if the cap were ever raised for one module. So the
    per-flap maximum and the widest line the modules can spell are both derived
    here from the file rather than asserted about it.
    """
    longest = max(
        (alternative for slot in BOARD.slots for alternative in slot.alternatives),
        key=len,
    )
    assert len(longest) <= FLAP_CAP, f"{longest!r} is {len(longest)} characters"

    for number in BOARD.lines:
        slots = BOARD.for_line(number).slots
        widest = sum(max(len(a) for a in slot.alternatives) for slot in slots) + len(slots) - 1
        assert widest <= BOARD_COLUMNS, f"line {number + 1} can assemble {widest} columns"


def test_a_spun_poem_reads_back_as_the_flaps_it_was_spun_from() -> None:
    """`segment` finds *a* reading; this asks that it find *the* one.

    Two modules of a line could between them spell the same words with the cut in
    a different place, and then a poem off the board would still check out while
    `flap_indices` reported flaps that were never turned. Nothing in the schema
    forbids that — it is a property of the strings, so it is tested on them.
    """
    for seed in range(64):
        turned = devices.spin(BOARD, seed)
        expected = [
            slot.alternatives.index(flap) for slot, flap in zip(BOARD.slots, turned, strict=True)
        ]
        assert flap_indices(spun(seed)) == expected, f"seed {seed} reads back as other flaps"


# ── the echo detector ──────────────────────────────────────────────────────
#
# Two flaps of one line that carry the same word read as a defect rather than as
# the machine being strange: "Der Hafen ... am Hafen". Comparing word forms is
# not enough, because German inflects — "vor Tagen" and "bei Tag" are the same
# word and an exact sweep calls them different. So flaps are compared by a
# stripped stem.
#
# The stemmer is deliberately crude and deliberately does *not* decompound:
# "Montag" and "Tage" stay distinct, as do "Umlauf" and "Vorlauf". Decompounding
# German with a rule would report far more pairs than it should, and the pairs it
# would find are ones a reader does not hear as repetition. What it does catch is
# plural and case endings and the umlaut that often comes with them, which is the
# class that actually escapes an exact sweep.

_UMLAUTS = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss"})

#: Longest first, so "-ern" is tried before "-er" and "-en" before "-n".
_ENDINGS = ("ern", "en", "er", "es", "em", "e", "n", "s")

#: Articles and prepositions repeat by construction — every PP module carries the
#: same preposition series — so they are not what this looks at.
# fmt: off
_FUNCTION_WORDS = frozenset([
    "der", "die", "das", "dem", "den",
    "im", "am", "in", "auf", "unter", "über", "ohne", "gegen", "nach", "seit",
    "mit", "aus", "bei", "vor", "trotz", "zu", "zur", "ab", "laut", "um",
    "von", "an", "durch", "per",
])
# fmt: on


def stem(word: str) -> str:
    """`word` with its umlauts folded and at most one inflectional ending removed.

    Stripping stops before the stem falls under three characters, which keeps
    "Eis" from becoming "Ei" and "Not" from colliding with everything short.
    """
    base = word.casefold().translate(_UMLAUTS)
    for ending in _ENDINGS:
        if base.endswith(ending) and len(base) - len(ending) >= 3:
            return base[: -len(ending)]
    return base


def content_stems(filler: str) -> set[str]:
    return {stem(word) for word in filler.split() if word.casefold() not in _FUNCTION_WORDS}


def test_the_stemmer_folds_the_endings_it_claims_to() -> None:
    """The detector below is only worth having if this is right, and a stemmer
    that quietly stopped folding would make it pass by finding nothing."""
    assert stem("Tagen") == stem("Tag")
    assert stem("Jahren") == stem("Jahre")
    assert stem("Häfen") == stem("Hafen")
    assert stem("Wachen") == stem("Wache")
    # Not decompounded, and not over-stripped.
    assert stem("Montag") != stem("Tage")
    assert stem("Umlauf") != stem("Vorlauf")
    assert stem("Eis") == "eis"


def test_no_line_can_show_one_word_twice() -> None:
    """No two modules of a line carry the same word, however inflected."""
    for number in BOARD.lines:
        slots = BOARD.for_line(number).slots
        reached: dict[str, dict[int, set[str]]] = {}
        for position, slot in enumerate(slots):
            for alternative in slot.alternatives:
                for key in content_stems(alternative):
                    reached.setdefault(key, {}).setdefault(position, set()).add(alternative)
        echoes = {key: spread for key, spread in reached.items() if len(spread) > 1}
        assert not echoes, f"line {number + 1} can show one word twice: {echoes}"


def test_no_line_can_show_two_incompatible_time_anchors() -> None:
    """Absurdity is the machine's business; contradiction is not.

    `Der Frost gedeiht` is strange and stays — the board is allowed to be strange.
    Two clock times in one line are not strange but broken, because they fix the
    same event at two hours, and the same goes for two calendar `seit` anchors and
    for two months. So each family is confined to a single module per line, where
    alternatives can never co-occur, which is also why all ten clock times survive
    on a board of only six lines.

    Families the line is deliberately *not* drawn around: `seit Jahren` beside
    `über Nacht`, or `um acht` beside `gegen Abend`, which differ in granularity
    and stack as a reader would stack them.
    """
    families = {
        "clock time": re.compile(
            r"^[Uu]m (eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf)$"
        ),
        "seit anchor": re.compile(r"^[Ss]eit "),
        # Only the punctual "im <month>" form. "ab Mai" and "zu Ostern" name a
        # start and a date rather than a when, and stack with a month without
        # contradicting it.
        "month or season": re.compile(
            r"^[Ii]m (Januar|Februar|März|April|Mai|Juni|Juli|August|September"
            r"|Oktober|November|Dezember|Winter|Frühjahr|Sommer|Herbst)$"
        ),
    }
    for name, pattern in families.items():
        for number in BOARD.lines:
            bearing = {
                position: [a for a in slot.alternatives if pattern.search(a)]
                for position, slot in enumerate(BOARD.for_line(number).slots)
                if any(pattern.search(a) for a in slot.alternatives)
            }
            assert len(bearing) <= 1, f"line {number + 1} can show two of {name}: {bearing}"

    clock = families["clock time"]
    total = sum(1 for slot in BOARD.slots for a in slot.alternatives if clock.match(a))
    assert total == 10, f"the board carries {total} clock times, not ten"


def test_the_positive_fixtures_show_no_word_twice() -> None:
    """The within-line rule cannot reach across lines, and a showcase poem that
    says "Der Kies" in line 2 and "mit Kies" in line 4 is an unlucky draw being
    presented as what the board does. The two positive fixtures are chosen, so
    they are held to the stricter rule the modules cannot enforce."""
    for case in harness.golden_cases():
        if case.procedure != "poesie_automat" or not case.satisfied:
            continue
        seen: dict[str, list[str]] = {}
        for word in case.text.split():
            if word.casefold() not in _FUNCTION_WORDS:
                seen.setdefault(stem(word), []).append(word)
        repeated = {key: words for key, words in seen.items() if len(words) > 1}
        assert not repeated, f"{case.name} repeats {repeated}"


# ── check ──────────────────────────────────────────────────────────────────


def test_a_poem_off_the_board_is_one_the_board_admits() -> None:
    for seed in range(16):
        poem = spun(seed)
        assert check("poesie_automat", poem, lang="de").satisfied, poem


def test_spinning_is_deterministic_under_a_seed() -> None:
    assert spun(5) == spun(5)
    assert spun(5) != spun(6)


def test_a_word_on_no_flap_names_its_module_and_its_line() -> None:
    poem = spun(0).splitlines()
    poem[2] = poem[2].replace("knistert", "explodiert")
    report = check("poesie_automat", "\n".join(poem), lang="de")
    assert not report.satisfied
    assert len(report.violations) == 1
    violation = report.violations[0]
    assert violation.rule == "module_not_on_the_board"
    assert "module 2 (Verb) of line 3" in violation.expected


def test_a_line_the_board_can_show_in_another_row_is_still_refused() -> None:
    """The modules are per line. A line 5 the board shows in row five is not a
    line 1, which is what makes the count 10^36 and not 10^6."""
    lines = spun(0).splitlines()
    lines[0], lines[4] = lines[4], lines[0]
    report = check("poesie_automat", "\n".join(lines), lang="de")
    assert not report.satisfied
    assert {v.rule for v in report.violations} == {"module_not_on_the_board"}
    assert report.score == pytest.approx(4 / 6)


def test_a_missing_line_is_reported_rather_than_ignored() -> None:
    report = check("poesie_automat", "\n".join(spun(0).splitlines()[:4]), lang="de")
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["missing_line", "missing_line"]


def test_a_seventh_line_is_an_extra_line() -> None:
    poem = spun(0)
    report = check("poesie_automat", poem + "\n" + poem.splitlines()[0], lang="de")
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["extra_line"]


def test_whitespace_between_flaps_is_normalised() -> None:
    poem = spun(0).replace(" ", "   ")
    assert check("poesie_automat", poem, lang="de").satisfied


def test_the_metrics_carry_the_module_and_combination_counts() -> None:
    report = check("poesie_automat", spun(0), lang="de")
    assert report.metrics["modules"] == 36.0
    assert report.metrics["lines"] == 6.0
    assert report.metrics["combinations"] == float(10**36)


def test_nonsense_is_not_on_the_board() -> None:
    assert not check(
        "poesie_automat", "xyzzy\nxyzzy\nxyzzy\nxyzzy\nxyzzy\nxyzzy", lang="de"
    ).satisfied


# ── the Device change is additive ──────────────────────────────────────────


def test_a_device_that_never_mentions_a_line_reads_as_one_line() -> None:
    """Harsdörffer's file is untouched and must stay a flat, single-line device."""
    assert all(slot.line == 0 for slot in RINGS.slots)
    assert RINGS.lines == [0]
    assert RINGS.for_line(0).slots == RINGS.slots
    assert RINGS.for_line(0).combinations == RINGS.combinations


def test_segment_without_a_separator_is_what_it_always_was() -> None:
    assert devices.segment("verlangen", RINGS) == ["ver", "L", "a", "ng", "en"]
    assert devices.segment("verlangen", RINGS, separator="") == ["ver", "L", "a", "ng", "en"]


def test_a_separator_is_expected_between_pieces_and_only_between_them() -> None:
    board = BOARD.for_line(0)
    line = spun(0).splitlines()[0]
    assert devices.segment(line, board, separator=" ") is not None
    # The same words run together spell nothing: the walk wants its spaces.
    assert devices.segment(line.replace(" ", ""), board, separator=" ") is None


def test_the_two_positive_fixtures_share_no_flap() -> None:
    """The second fixture's `source` claims its thirty-six modules all differ from
    the first's. That is a claim shipped inside the package, in the field that
    exists to record provenance, so it is re-derived here rather than trusted:
    the seed that stood there first shared six modules and the sentence was
    false for as long as it shipped.
    """
    positive = [
        case
        for case in harness.golden_cases()
        if case.procedure == "poesie_automat" and case.satisfied
    ]
    assert len(positive) == 2
    first, second = (flap_indices(case.text) for case in positive)
    assert len(first) == len(second) == 36
    shared = [i for i, (a, b) in enumerate(zip(first, second, strict=True)) if a == b]
    assert not shared, f"modules {shared} show the same flap in both fixtures"


# ── the optional-slot branch, which no shipped device can reach ─────────────


def _optional_device(*, optional: int) -> Device:
    """Three slots carrying whole words, one of them skippable.

    No device this package ships combines an optional slot with a non-empty
    separator — Harsdörffer's rings have optional slots and concatenate with
    nothing between them, and the flap-board has a separator and no optional
    slots. So the `emitted` bookkeeping in `segment` is reachable only from a
    device built here.
    """
    return Device(
        id="synthetic",
        name="synthetic",
        source="constructed for this test",
        slots=[
            Slot(name=str(n), alternatives=[word], optional=(n == optional))
            for n, word in enumerate(("alpha", "beta", "gamma"))
        ],
    )


def test_a_skipped_first_slot_leaves_no_separator_to_consume() -> None:
    """The mutation this kills: treating a skipped optional slot as though it had
    emitted a piece. Then the walk would demand a leading space before "beta"
    and the whole reading would fail."""
    device = _optional_device(optional=0)
    assert devices.segment("alpha beta gamma", device, separator=" ") == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert devices.segment("beta gamma", device, separator=" ") == ["", "beta", "gamma"]
    # The orphaned separator a naive implementation would accept.
    assert devices.segment(" beta gamma", device, separator=" ") is None


def test_a_skipped_middle_slot_does_not_double_the_separator() -> None:
    device = _optional_device(optional=1)
    assert devices.segment("alpha beta gamma", device, separator=" ") == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert devices.segment("alpha gamma", device, separator=" ") == ["alpha", "", "gamma"]
    assert devices.segment("alpha  gamma", device, separator=" ") is None


def test_a_skipped_last_slot_leaves_no_trailing_separator() -> None:
    device = _optional_device(optional=2)
    assert devices.segment("alpha beta", device, separator=" ") == ["alpha", "beta", ""]
    assert devices.segment("alpha beta ", device, separator=" ") is None
