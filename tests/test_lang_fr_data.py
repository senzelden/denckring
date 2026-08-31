"""The French lexicon's own invariants.

Skipped in full when `denckring[fr]` is not installed, exactly as the German and
English data tests skip without theirs.
"""

import gzip
import json
from pathlib import Path

import pytest

fr_data = pytest.importorskip("denckring_fr_data", reason="needs denckring[fr]")

DATA = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "denckring-fr-data"
    / "src"
    / "denckring_fr_data"
    / "data"
)


def test_the_distribution_is_importable_and_versioned() -> None:
    assert fr_data.__version__ == "0.1.0"


def test_the_bands_run_the_project_s_way_and_not_the_source_s() -> None:
    """Lexique's frequencies rise with commonness; `graded_words` bands fall with
    it, matching SCOWL and what `anagram` sorts by. The build inverts, and a
    source's convention leaking through here would silently rank every French
    anagram backwards. ADR 0032.

    `nonobstant` was the planned second word, but in the built table it lands in
    the same band as `être`: Lexique's `freqlivres` gives it 2.97 per million,
    which ranks it inside the top 14% of forms (book corpora carry a lot of
    formal/legal prose), so the six-band rank split does not separate the pair.
    `obsolescence` is genuinely rare in this table (band 60) and stands in for it.
    """
    bands = fr_data.graded_words()
    assert bands["être"] < bands["obsolescence"]
    assert set(bands.values()) <= {10, 20, 30, 40, 50, 60}


def test_the_noun_list_is_ordered_and_deep() -> None:
    """N+7 indexes into this positionally, so the order is load-bearing."""
    nouns = fr_data.noun_list()
    assert list(nouns) == sorted(nouns)
    assert len(nouns) > 40_000
    assert "maison" in nouns


def test_membership_is_broad_and_keeps_accents() -> None:
    words = fr_data.known_words()
    for word in ("maison", "aimait", "côte", "être"):
        assert word in words


def test_glosses_carry_every_sense_in_wiktionary_s_order() -> None:
    """Every sense, not the first: which sense a writer meant is not knowable from
    the text, so a caller that accepts any of them is the honest reader."""
    senses = fr_data.gloss_table()["maison"]
    assert len(senses) > 3
    assert "bâtiment" in senses[0].casefold()


def test_a_headword_with_no_definition_is_absent_rather_than_empty() -> None:
    assert "zzzzqq" not in fr_data.gloss_table()


def test_the_metadata_counts_match_the_files() -> None:
    """A silent corpus change fails here rather than drifting unnoticed. The
    gzip bytes alone do not diff cleanly enough to catch it by eye."""
    counts = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))["counts"]
    for name, expected in counts.items():
        with gzip.open(DATA / name, mode="rt", encoding="utf-8") as handle:
            assert sum(1 for _ in handle) == expected, name
