"""The rows defined on letters must never take a pronunciation judgement.

`univocalic` and its neighbours are `family: letter`, sourced to Bombaugh (1867)
and Word Ways, and declare `requires: [tokens, alphabet, fold_diacritics]` with
no `phonemes`. A glide-aware reading — `y w u i o` in English, `y i u ou` in
French — is measurably correct linguistically and measurably wrong here: it
makes each of the words below a univocalic, which no Word Ways editor accepts.

This is the test that fails if such a rule is ever wired into these rows. It
guards a boundary rather than an implementation, so it holds whether or not the
phonetic reading has been built — and it has not been: `letter_classes()` is
deferred, and `spoonerism` still splits an onset on flat `vowels()` membership.
ADR 0035, D2.
"""

from denckring import check
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures

#: Each of these has exactly one *phonetic* vowel and more than one vowel
#: *letter*, so a glide-aware reading would call it univocalic.
GLIDE_WORDS = ["onion", "quick", "million", "oui", "huit", "nuit", "lui"]

#: The rows whose reading is orthographic, by their own `requires`.
ORTHOGRAPHIC = ("univocalic", "bivocalic", "monoconsonantal", "supervocalic")

#: Both languages whose packs would carry a glide inventory of their own.
LANGUAGES: tuple[Lang, ...] = ("en", "fr")


def test_no_glide_word_is_a_univocalic() -> None:
    for word in GLIDE_WORDS:
        for lang in LANGUAGES:
            assert not check("univocalic", word, lang=lang).satisfied, (
                f"{word!r} became a univocalic in {lang}: the phonetic reading has "
                f"leaked into a row that declares no phonemes"
            )


def test_the_orthographic_rows_declare_no_phonemes() -> None:
    """The premise of the test above, asserted rather than assumed — if a row
    ever gains `phonemes` this test says so before the one above starts lying.
    """
    for pid in ORTHOGRAPHIC:
        requires = all_procedures()[pid].meta.requires
        assert "phonemes" not in requires, (
            f"{pid} now declares phonemes; D2's licensing argument has to be revisited "
            f"before it may read a phonetic classification"
        )


def test_spoonerism_is_the_licensed_row() -> None:
    """The one consumer D2 licenses for the contextual reading, whenever it is
    built. Nothing here asserts that it has been.
    """
    assert "phonemes" in all_procedures()["spoonerism"].meta.requires
