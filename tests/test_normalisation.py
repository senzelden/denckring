"""A text's Unicode normalisation form must not change a verdict.

`ä` is two strings: one character in NFC, and `a` followed by U+0308 in NFD. A
reader cannot tell them apart, a keyboard produces either depending on the
platform — macOS filenames are NFD — and until this file existed nothing here
said the two had to agree.

They did not. `letter_spans` walked the text character by character and kept
what `isalpha()` accepted, so a combining mark, which is `Mn` and not alphabetic,
was dropped while the bare `a` under it was kept. Folding hid this: with
`fold_diacritics` on, both forms answer `a` and the bug is invisible. With it
*off* — the setting whose entire documented purpose is that `ä` stays `ä` — the
decomposed form silently folded anyway, and the flag did the opposite of what it
promises.

The verdict it changed, measured before the fix: `check("lipogram", "Bär",
forbidden="a", fold_diacritics=False)` is satisfied on NFC and *unsatisfied* on
NFD, because the `a` exposed by decomposition is a letter the lipogram forbids.

Every golden fixture in this repository is NFC, which is why 532 of them agreed
with the implementation about a case none of them contained. That is the shape
of defect an author's own examples cannot find.

Offsets are deliberately not compared across forms: the two strings have
different lengths, so an offset into one is not an offset into the other. What
must agree is the sequence of letters, and the verdict that follows from it.
"""

from __future__ import annotations

import unicodedata

import pytest

from denckring import check
from denckring.core.text import letter_spans
from denckring.lang import get_pack

PACK = get_pack("en")

#: Words whose NFC and NFD forms differ, one per language this package serves.
#: A word with no combining mark available would normalise to itself and prove
#: nothing, which is the discipline `test_fold_symmetry` records for its own list.
DECOMPOSABLE = ["Bär", "café", "Grüße", "élève", "Öl"]


@pytest.mark.parametrize("word", DECOMPOSABLE)
@pytest.mark.parametrize("fold", [True, False])
def test_letter_spans_read_both_normalisation_forms_alike(word: str, fold: bool) -> None:
    """The letters, not the offsets — the two strings have different lengths."""
    nfc = unicodedata.normalize("NFC", word)
    nfd = unicodedata.normalize("NFD", word)
    assert nfc != nfd, f"{word!r} normalises to itself and discriminates nothing"
    assert [letter for _, letter in letter_spans(nfc, PACK, fold=fold)] == [
        letter for _, letter in letter_spans(nfd, PACK, fold=fold)
    ]


def test_unfolded_spans_keep_the_diacritic_they_promise_to_keep() -> None:
    """`fold_diacritics=False` says `ä` stays `ä`, and that has to be true of the
    decomposed spelling too — otherwise the flag folds exactly what it exists to
    preserve, and does it only for text that arrived in the other form."""
    nfd = unicodedata.normalize("NFD", "Bär")
    assert [letter for _, letter in letter_spans(nfd, PACK, fold=False)] == ["b", "ä", "r"]


def test_offsets_still_point_into_the_text_they_were_read_from() -> None:
    """Composing a cluster must not cost the offset of its base character, which
    is what `Violation.offset` is and what the explorer marks text with."""
    nfd = unicodedata.normalize("NFD", "Bär")
    assert letter_spans(nfd, PACK, fold=False) == [(0, "b"), (1, "ä"), (3, "r")]


@pytest.mark.parametrize("fold", [True, False])
def test_a_lipogram_verdict_survives_normalisation(fold: bool) -> None:
    """The end the helper is a means to. `a` is not in `Bär` under either
    spelling, and only one of the two used to say so."""
    verdicts = {
        check(
            "lipogram",
            unicodedata.normalize(form, "Bär"),
            lang="de",
            forbidden="a",
            fold_diacritics=fold,
        ).satisfied
        for form in ("NFC", "NFD")
    }
    assert len(verdicts) == 1, "the same word gets opposite verdicts by normalisation form"


def test_zero_width_and_invisible_characters_are_not_letters() -> None:
    """Pinning what was already true, because nothing said so. A zero-width
    space, a BOM and a non-breaking space are not alphabetic and must not become
    letters, must not join the cluster before them, and must not shift the
    offsets of the letters around them."""
    assert letter_spans("a\u200bb", PACK) == [(0, "a"), (2, "b")]
    assert letter_spans("\ufeffab", PACK) == [(1, "a"), (2, "b")]
    assert letter_spans("a\u00a0b", PACK) == [(0, "a"), (2, "b")]


def test_a_glyph_verdict_survives_normalisation() -> None:
    """The second instance of the same defect, and the one folding could never
    have hidden: `prisoners_constraint` asks whether a written character stays
    within the x-height, so it must never fold — the README's own example is that
    `Masse` satisfies it and `Maße` does not.

    Walking characters, a decomposed `ä` presented as a bare `a`, which is within
    the x-height, and the umlaut above it was dropped before anything could ask.
    Measured before the fix: `Bär` scored 0.333 in NFC and 0.667 in NFD, and the
    NFD reading listed one violation where there are two.
    """
    reports = [
        check("prisoners_constraint", unicodedata.normalize(form, "Bär"), lang="de")
        for form in ("NFC", "NFD")
    ]
    assert reports[0].score == pytest.approx(reports[1].score)
    assert reports[0].score == pytest.approx(1 / 3)
    # `found` echoes the text as written, so the decomposed report carries the
    # decomposed cluster — the same two characters the caller passed. What has to
    # agree is which characters were condemned, not how they were spelled.
    assert [
        [unicodedata.normalize("NFC", v.found) for v in report.violations] for report in reports
    ] == [["B", "ä"]] * 2
