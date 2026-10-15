"""The klingende Kadenz, per row that can now express it (ADR 0040 D1)."""

from __future__ import annotations

import pytest

from denckring import check

#: Goethe, Iphigenie auf Tauris (1787), I.1 — German blank verse, whose endings
#: are predominantly feminine. Eleven syllables to the pentameter's ten.
IPHIGENIE = """Heraus in eure Schatten, rege Wipfel
Des alten, heil'gen, dichtbelaubten Haines,
Wie in der Göttin stilles Heiligthum
Tret' ich noch jetzt mit schauderndem Gefühl,
Als wenn ich sie zum erstenmal beträte,
Und es gewöhnt sich nicht mein Geist hierher."""


def test_german_blank_verse_needs_the_feminine_ending() -> None:
    """Without it the row rejects Goethe, which is today's reading and stays so."""
    assert not check("blank_verse", IPHIGENIE, lang="de").satisfied


def test_german_blank_verse_scans_far_better_with_it() -> None:
    """Not `satisfied` — three of these six lines carry a separate stress
    disagreement that D1 does not reach and D4 declines to fix. The claim is that
    the parameter moves the score, not that it rescues the poem."""
    strict = check("blank_verse", IPHIGENIE, lang="de").score
    loose = check("blank_verse", IPHIGENIE, lang="de", feminine_ending=True).score
    assert loose > strict


@pytest.mark.parametrize(
    "procedure",
    [
        "blank_verse",
        "shakespearean_sonnet",
        "rhyme_royal",
        "curtal_sonnet",
        "sonnet",
        "ottava_rima",
        "petrarchan_sonnet",
        "iambic_pentameter",
        "heroic_couplet",
        "ballade",
    ],
)
def test_every_wired_row_accepts_the_parameter(procedure: str) -> None:
    """The parameter is in the schema. Whether the row passes it on is the next test's
    question: a row that took it and dropped it would pass this one."""
    from denckring.core.registry import get

    assert "feminine_ending" in get(procedure).params_model().model_fields


#: One iambic line per length, each closing on one extra unstressed syllable
#: (`water`, 10). Only the metre is asserted on below, so the rhyme it breaks is beside
#: the point.
FEMININE_LINES = {
    "0101010101": "the cat can see the moon above the water",
    "01010101": "the cat can see above the water",
}
METRE_RULES = {"wrong_line_length", "wrong_stress"}


@pytest.mark.parametrize(
    "procedure", ["iambic_pentameter", "heroic_couplet", "ballade", "petrarchan_sonnet"]
)
def test_every_row_new_to_the_parameter_passes_it_to_the_scan(procedure: str) -> None:
    """The four rows ADR 0065 gave `feminine_ending`, by behaviour: a satisfied golden
    case with its first line made feminine fails on metre with the switch off and
    carries no metre fault with it on. A row that took the parameter and never handed
    it to the scan fails the second half."""
    from conftest import load_golden_cases

    case = next(
        c
        for c in load_golden_cases()
        if c.procedure == procedure
        and c.satisfied
        and c.lang == "en"
        # A ballade with `metre` unset scans nothing, so it cannot fail on metre.
        and c.params.get("metre", "") is not None
    )
    metre = case.params.get("metre") or ("01010101" if procedure == "ballade" else "0101010101")
    lines = case.text.split("\n")
    text = "\n".join([FEMININE_LINES[metre], *lines[1:]])
    params = {k: v for k, v in case.params.items() if k != "feminine_ending"}

    def metre_faults(on: bool) -> set[str]:
        report = check(procedure, text, lang="en", **params, feminine_ending=on)
        return {v.rule for v in report.violations} & METRE_RULES

    assert metre_faults(False)
    assert not metre_faults(True)


def test_the_spenserian_alexandrine_may_also_close_feminine() -> None:
    """The ninth line is the form; widening the other eight and not it would be
    a bug the stanza's own shape hides."""
    from denckring.procedures.spenserian_stanza import patterns

    strict = patterns(False)
    loose = patterns(True)
    assert strict[0] == ["0101010101"]
    assert loose[0] == ["0101010101", "01010101010"]
    assert loose[8] == ["010101010101", "0101010101010"]


#: A constructed ottava rima whose couplet closes feminine, as Byron's do: eleven
#: syllables, the eleventh unstressed. `billow` was chosen before 0.6.0, when the
#: rhyme key kept the secondary stress the dictionary gives willow's last vowel; the key
#: now folds it (ADR 0057), so `willow` would rhyme here too.
FEMININE_COUPLET = """the cat can see the moon above the tree
the dog will run across the field today
a kestrel flies around the house at three
the sun will set behind the hill in may
the owl will call across the dark at sea
the fox will hide beneath the fallen way
the mice will creep beside the ancient billow
the birds will sleep upon a feather pillow"""


def test_ottava_rima_admits_a_feminine_couplet_only_when_asked() -> None:
    """Off by default, so 0.5.0's verdict on every text stands; on, the two
    eleven-syllable lines are the only fault and they go."""
    strict = check("ottava_rima", FEMININE_COUPLET)
    assert not strict.satisfied
    assert {v.rule for v in strict.violations} == {"wrong_line_length"}
    assert check("ottava_rima", FEMININE_COUPLET, feminine_ending=True).satisfied


#: Gryphius, "Thränen des Vaterlandes" (1636), ll.1-2. German alexandriners,
#: the first closing feminine at thirteen syllables.
GRYPHIUS = """Wir sind doch nunmehr gantz/ ja mehr denn gantz verheeret!
Der frechen Völcker Schaar/ die rasende Posaun"""


def test_a_german_alexandriner_may_close_on_thirteen() -> None:
    strict = check("alexandrine", GRYPHIUS, lang="de")
    loose = check("alexandrine", GRYPHIUS, lang="de", feminine_ending=True)
    assert not strict.satisfied
    assert loose.score > strict.score


def test_the_tolerance_is_one_syllable_and_only_at_the_close() -> None:
    """A guard that admitted any count would pass this row on anything."""
    fourteen = "Wir sind doch nunmehr gantz und gar und ganz und gar verheeret schon"
    assert not check("alexandrine", fourteen, lang="de", feminine_ending=True).satisfied
