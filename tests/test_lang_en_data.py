"""The English data files are now reproducible, as the German ones already were."""

import gzip
import json
from pathlib import Path

import pytest

en_data = pytest.importorskip("denckring_en_data", reason="needs denckring[en]")

DATA = Path(en_data.__file__).parent / "data"


def _read_gz(path: Path) -> list[str]:
    return gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()


def test_shipped_files_match_the_recorded_metadata_counts() -> None:
    """`nouns.txt` was hand-extracted and committed with no script, so nothing
    could tell whether it had drifted. `metadata.json` records the counts beside
    the data, and a truncated download or bad regeneration fails here loudly."""
    metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
    nouns = (DATA / "nouns.txt").read_text(encoding="utf-8").split()
    glosses = _read_gz(DATA / "glosses.txt.gz")
    assert len(nouns) == metadata["counts"]["nouns.txt"]
    assert len(glosses) == metadata["counts"]["glosses.txt.gz"]


def test_the_metadata_names_the_wordnet_version_it_came_from() -> None:
    """The previous list recorded nothing, which is why establishing its
    provenance took a licence file and a guess."""
    metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
    assert "oewn" in metadata["source"].lower()
    assert "2024" in metadata["source"]


def test_the_graded_list_ships_the_words_the_search_needs() -> None:
    """The five words the chapter turns on, and the four it must have dropped."""
    graded = en_data.graded_words()
    for word in ("room", "dirty", "silent", "listen", "tinsel"):
        assert word in graded, f"{word} missing: the famous covers are unreachable"
    for surname in ("dority", "romito", "stinel", "sutphen"):
        assert surname not in graded, (
            f"{surname} present: proper names are what made the old oracle unrankable"
        )


def test_common_words_sit_in_lower_bands_than_rare_ones() -> None:
    """SCOWL's numbering runs backwards from intuition: larger means less common.
    The whole ranking rests on this, so it is asserted rather than assumed."""
    graded = en_data.graded_words()
    assert graded["room"] < 60
    assert graded["dirty"] < 60


def test_the_shipped_counts_match_the_metadata() -> None:
    """A silent corpus change fails loudly instead of drifting unnoticed — the
    same guard `denckring-de-data` puts on its two files."""
    metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
    assert len(en_data.graded_words()) == metadata["counts"]["graded_words.txt.gz"]
