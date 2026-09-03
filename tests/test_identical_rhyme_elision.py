"""Elision defeated `identical_rhyme` on every rhyme row.

`identical` compared each line's final word as written: `l'amour` and `amour`
are the same rhyme word in French, but the comparison never split the
proclitic off, so a minimal pair differing only by a leading `l'` matched by
`does_rhyme` and by neither `identical_rhyme` nor `does_not_rhyme`, scoring
1.0 where the bare pair correctly failed. Sharper than a generic gap:
`hemeling` publishes `allow_identical` as "Permit a word to rhyme with
itself, as French rime riche does" — the row explicitly models French
self-rhyme, and the dial was bypassed by the commonest orthographic fact in
the language. ADR 0036.
"""

import pytest

from denckring import check

pytest.importorskip("denckring_fr_data")


def test_an_elided_and_a_bare_form_of_the_same_word_are_identical() -> None:
    report = check(
        "rhyme_scheme", "Il chante leur amour\nIl pense à l'amour", lang="fr", scheme="AA"
    )
    assert not report.satisfied
    assert report.violations[0].rule == "identical_rhyme"


def test_allow_identical_still_permits_the_elided_pair() -> None:
    assert check(
        "rhyme_scheme",
        "Il chante leur amour\nIl pense à l'amour",
        lang="fr",
        scheme="AA",
        allow_identical=True,
    ).satisfied


def test_a_genuine_rhyme_across_an_elision_boundary_still_holds() -> None:
    """Not every pair spanning an apostrophe is identical — this guards
    against a fix that over-corrects into flagging every elided line as a
    forbidden self-rhyme."""
    report = check(
        "rhyme_scheme", "Il chante notre douleur\nIl pense à l'ampleur", lang="fr", scheme="AA"
    )
    assert report.violations == []


def test_hemeling_inherits_the_fix() -> None:
    """`hemeling` reuses `rhyme_scheme.form_report`, so the fix reaches it
    without a change of its own."""
    text = "aimer\nOn voit Marie qui sait leur amour\nElle chante à l'amour"
    report = check("hemeling", text, lang="fr", source="Marie")
    assert not report.satisfied
    assert any(v.rule == "identical_rhyme" for v in report.violations)
