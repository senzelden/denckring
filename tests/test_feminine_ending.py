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
    ["blank_verse", "shakespearean_sonnet", "rhyme_royal", "curtal_sonnet", "sonnet"],
)
def test_every_wired_row_accepts_the_parameter(procedure: str) -> None:
    """A row that silently ignored it would look wired and not be."""
    from denckring.core.registry import get

    assert "feminine_ending" in get(procedure).params_model().model_fields


def test_the_spenserian_alexandrine_may_also_close_feminine() -> None:
    """The ninth line is the form; widening the other eight and not it would be
    a bug the stanza's own shape hides."""
    from denckring.procedures.spenserian_stanza import patterns

    strict = patterns(False)
    loose = patterns(True)
    assert strict[0] == ["0101010101"]
    assert loose[0] == ["0101010101", "01010101010"]
    assert loose[8] == ["010101010101", "0101010101010"]
