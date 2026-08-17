"""The German lexicon's own invariants.

Skipped in full when `denckring[de]` is not installed, exactly as the English
data tests skip without `denckring[en]`. The eszett-folding test below is the
exception: it reads the vendored .gz files directly rather than through the
`denckring_de_data` package, so it still runs even though the package (a
later task) does not exist yet.
"""

import gzip
import json
import re
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from denckring import check
from denckring.lang import get_pack
from denckring.procedures.charade import splits_into

SINGLE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")

DATA = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "denckring-de-data"
    / "src"
    / "denckring_de_data"
    / "data"
)

try:
    import denckring_de_data as de_data
except ModuleNotFoundError:
    de_data = None  # type: ignore[assignment]

#: Applied to the tests below that reference `de_data` directly rather than
#: through the fixture, so they skip - rather than error - when the package
#: is absent. Collection-time skip is deliberately avoided (no module-level
#: `importorskip`): it would also skip the eszett-folding test above, which
#: must keep running even when the package does not exist.
requires_de_data = pytest.mark.skipif(de_data is None, reason="denckring-de-data is not installed")


@pytest.fixture(name="de_data")
def _de_data_fixture() -> ModuleType:
    return cast(ModuleType, pytest.importorskip("denckring_de_data"))


def _read_gz(path: Path) -> list[str]:
    return gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()


def test_shipped_files_match_the_recorded_metadata_counts() -> None:
    """ADR 0023 claims the vendored files are reproducible; `metadata.json`
    records the entry counts alongside them so a silent corpus change (a
    truncated download, a bad regeneration) fails this test loudly instead
    of drifting unnoticed, since the gzip bytes themselves do not diff
    cleanly enough to catch that by eye."""
    metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
    nouns = _read_gz(DATA / "nouns.txt.gz")
    words = _read_gz(DATA / "words.txt.gz")
    assert len(nouns) == metadata["counts"]["nouns.txt.gz"]
    assert len(words) == metadata["counts"]["words.txt.gz"]


def test_noun_list_is_single_token_and_alphabetic(de_data: ModuleType) -> None:
    """ADR 0015's rule: N+7 walks this list and needs whole tokens."""
    nouns = de_data.noun_list()
    assert len(nouns) > 100_000
    offenders = [w for w in nouns if not SINGLE_TOKEN.fullmatch(w)]
    assert not offenders[:10], f"multi-token or non-alphabetic lemmas: {offenders[:10]}"


def test_noun_list_is_capitalised_as_german_nouns_are(de_data: ModuleType) -> None:
    nouns = de_data.noun_list()
    assert all(w[:1].isupper() for w in nouns[:1000])


def test_noun_list_is_in_dictionary_order(de_data: ModuleType) -> None:
    nouns = de_data.noun_list()
    assert list(nouns) == sorted(nouns)


def test_membership_covers_more_than_nouns(de_data: ModuleType) -> None:
    """A noun-only oracle would reject `singen` and `rot`."""
    known = de_data.known_words()
    assert "singen" in known
    assert "rot" in known


def test_membership_folds_eszett_deliberately_while_the_noun_list_keeps_it() -> None:
    """casefold() intentionally maps ß -> "ss" when building the membership
    set (words.txt.gz), merging Swiss and German spellings of the same word
    (e.g. Maßen/Massen). Measured impact when the data was generated: 110
    collision keys covering 222 of 184,040 noun lemmas (0.12%) - all either
    ß/ss spelling variants or acronym case variants. Correct behaviour for a
    membership oracle, not lossy: str.lower() would keep ß but then miss an
    all-caps "STRASSE" and split Straße/Strasse into unrelated words, which
    is worse. nouns.txt.gz is never casefolded and keeps ß intact.

    This pins the behaviour as deliberate rather than an accident: if a
    future change swapped casefold() for lower() in the build script, this
    test fails loudly instead of silently drifting.
    """
    nouns = _read_gz(DATA / "nouns.txt.gz")
    words = set(_read_gz(DATA / "words.txt.gz"))

    eszett_noun = next(w for w in nouns if "ß" in w)
    assert eszett_noun in nouns  # the noun list preserves ß verbatim

    assert eszett_noun.casefold() in words  # the ss-folded spelling is stored
    assert eszett_noun.lower() not in words  # the ß spelling (via lower()) is not


@requires_de_data
def test_pack_declares_both_lexical_capabilities() -> None:
    from denckring.lang.base import NOUNS, WORDS

    pack = de_data.GermanDataPack()
    assert {NOUNS, WORDS} <= pack.capabilities


@requires_de_data
def test_is_word_knows_german() -> None:
    pack = de_data.GermanDataPack()
    assert pack.is_word("Katze")
    assert pack.is_word("katze"), "membership is case-insensitive"
    assert not pack.is_word("xqzzy")


@requires_de_data
def test_noun_index_finds_a_noun_and_rejects_a_non_noun() -> None:
    pack = de_data.GermanDataPack()
    assert pack.noun_index("Katze") is not None
    assert pack.noun_index("xqzzy") is None


@requires_de_data
def test_umlauts_are_kept_not_folded() -> None:
    """`fold_diacritics` would collide these two. ADR 0009 makes folding a
    procedure parameter, so the lexicon must not decide it for every caller."""
    pack = de_data.GermanDataPack()
    baer = pack.noun_index("Bär")
    bar = pack.noun_index("Bar")
    assert baer is not None and bar is not None
    assert baer != bar, "Bär and Bar must be distinct entries"


@requires_de_data
def test_eszett_is_kept() -> None:
    pack = de_data.GermanDataPack()
    assert pack.is_word("Straße")


@requires_de_data
def test_charade_with_an_umlaut_now_divides_correctly() -> None:
    """Before `charade` queried the lexicon with `fold=False`, `letter_spans`
    stripped the umlaut before the lookup, turning "Nachtwächter" into
    "nachtwachter" - and "wachter" is not a German word, so this genuine
    charade (Nacht + Wächter) was unreachable. It must now divide."""
    report = check("charade", "Nachtwächter", lang="de")
    assert report.satisfied


@requires_de_data
def test_charade_no_longer_assembles_a_division_from_folded_letters() -> None:
    """Before the fix, "Auslässe" was folded to "auslasse" before the lexicon
    query and satisfied `charade` via the split "aus" + "lasse" - a division
    built from letters ("lasse") that only exist once the umlaut has been
    silently discarded, not from what is literally written. With `fold=False`
    the lexicon is queried on "auslässe" as written, that split does not
    exist, and the word is correctly a violation.

    (This is not true of every umlaut word: "Bärlauch" stays satisfied after
    the fix too, but for a different, legitimate reason - "bär" (bear) and
    "lauch" (leek) are each independently real German words on their own, so
    "Bär" + "lauch" is a genuine division of the literal text, not a folding
    artefact. It is covered separately below.)"""
    report = check("charade", "Auslässe", lang="de")
    assert not report.satisfied
    assert report.violations[0].rule == "does_not_divide"


@requires_de_data
def test_charade_baerlauch_divides_on_the_literal_umlaut_not_a_folded_substitute() -> None:
    """ "Bärlauch" remains satisfied after the fix, but the division must use
    the literal letters ("bär", the German word for bear) rather than the
    pre-fix folded substitute ("bar", a different word obtained only by
    discarding the umlaut)."""

    pack = get_pack("de")
    assert splits_into("bärlauch", 2, pack) == ["bär", "lauch"]
