"""English word frequency from the Leipzig news corpus (audit D3, ADR 0052).

The build's case rule is tested against Leipzig-shaped rows, never a download:
the corpus is 288 MB. The shipped table is held to what the build promises of
it: graded words only, lowercase keys, and counts that rank function words
first.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

import denckring
from denckring.core.errors import MissingCapability, extra_for
from denckring.lang import get_pack
from denckring.lang.base import FREQUENCY, BasePack, graded_view

SCRIPTS = Path(__file__).parent.parent / "packages/denckring-en-data/scripts"
sys.path.insert(0, str(SCRIPTS))

from build_frequencies import counts  # noqa: E402

GRADED = {"bill": 20, "the": 10, "however": 10, "trump": 35}


def test_a_word_is_counted_only_as_written_in_lowercase() -> None:
    """`Bill` and `Trump` are names in news; their counts are not the nouns'."""
    rows = [("bill", 40), ("Bill", 9000), ("Trump", 50000), ("However", 300), ("however", 700)]
    assert counts(rows, GRADED) == {"bill": 40, "however": 700}


def test_only_graded_words_are_counted_and_the_largest_row_wins() -> None:
    rows = [("the", 10), ("the", 99), ("teh", 5000), ("2023", 8000)]
    assert counts(rows, GRADED) == {"the": 99}


def _english() -> BasePack:
    pack = get_pack("en")
    assert isinstance(pack, BasePack)
    return pack


def test_the_shipped_table_is_over_the_graded_vocabulary() -> None:
    pack = _english()
    assert FREQUENCY in pack.capabilities
    table = pack.word_frequencies()
    graded = pack.graded_words()
    assert sorted(word for word in table if word not in graded) == []
    assert all(word.islower() and count > 0 for word, count in table.items())
    metadata = json.loads(
        (
            Path(__file__).parent.parent
            / "packages/denckring-en-data/src/denckring_en_data/data/metadata.json"
        ).read_text(encoding="utf-8")
    )
    assert metadata["counts"]["frequencies.txt.gz"] == len(table)
    assert metadata["frequency"]["corpus"] == "eng_news_2023_1M"


def test_the_shipped_table_ranks_function_words_first() -> None:
    """A frequency, not a band: `the` above `cat` above `aardvark`."""
    table = _english().word_frequencies()
    assert table["the"] > table["cat"] > table.get("aardvark", 0)
    assert denckring.words("en", order="frequency")[:3] == ("the", "to", "and")


def test_the_shipped_file_is_reproducible_bytes() -> None:
    """Written with a zero gzip timestamp, so a rebuild from the same archive matches."""
    path = (
        Path(__file__).parent.parent
        / "packages/denckring-en-data/src/denckring_en_data/data/frequencies.txt.gz"
    )
    assert path.read_bytes()[4:8] == b"\x00\x00\x00\x00"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        words = [line.partition("\t")[0] for line in handle]
    assert words == sorted(words)


def test_frequency_order_is_by_count_then_word_with_absent_words_last() -> None:
    table = _english().word_frequencies()
    found = denckring.words("en", max_band=20, order="frequency")
    assert set(found) == set(denckring.words("en", max_band=20))
    keys = [(-table.get(word, 0), word) for word in found]
    assert keys == sorted(keys)


@pytest.mark.parametrize("lang", ["de", "fr"])
def test_a_language_without_counts_refuses_and_names_no_extra(lang: str) -> None:
    with pytest.raises(MissingCapability) as raised:
        denckring.words(lang, order="frequency")  # type: ignore[arg-type]
    assert raised.value.capability == FREQUENCY
    assert extra_for(lang, FREQUENCY) is None
    assert extra_for("en", FREQUENCY) == "en"


class _NoCounts:
    lang = "en"

    def graded_words(self) -> dict[str, int]:
        return {"a": 10}


def test_a_protocol_pack_without_counts_refuses_frequency_order() -> None:
    assert graded_view(_NoCounts()) == ("a",)
    with pytest.raises(MissingCapability):
        graded_view(_NoCounts(), order="frequency")
