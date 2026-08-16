"""The German lexicon's own invariants.

Skipped in full when `denckring[de]` is not installed, exactly as the English
data tests skip without `denckring[en]`. The eszett-folding test below is the
exception: it reads the vendored .gz files directly rather than through the
`denckring_de_data` package, so it still runs even though the package (a
later task) does not exist yet.
"""

import gzip
import re
from pathlib import Path

import pytest

SINGLE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")

DATA = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "denckring-de-data"
    / "src"
    / "denckring_de_data"
    / "data"
)


@pytest.fixture
def de_data():
    return pytest.importorskip("denckring_de_data")


def _read_gz(path: Path) -> list[str]:
    return gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()


def test_noun_list_is_single_token_and_alphabetic(de_data) -> None:
    """ADR 0015's rule: N+7 walks this list and needs whole tokens."""
    nouns = de_data.noun_list()
    assert len(nouns) > 100_000
    offenders = [w for w in nouns if not SINGLE_TOKEN.fullmatch(w)]
    assert not offenders[:10], f"multi-token or non-alphabetic lemmas: {offenders[:10]}"


def test_noun_list_is_capitalised_as_german_nouns_are(de_data) -> None:
    nouns = de_data.noun_list()
    assert all(w[:1].isupper() for w in nouns[:1000])


def test_noun_list_is_in_dictionary_order(de_data) -> None:
    nouns = de_data.noun_list()
    assert list(nouns) == sorted(nouns)


def test_membership_covers_more_than_nouns(de_data) -> None:
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
