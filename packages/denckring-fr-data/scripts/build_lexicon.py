"""Regenerate the vendored French lexicon from Lexique 3.82 and a Wiktionary dump.

Committed so the data files are reproducible and diffable, the convention
`denckring-de-data/scripts/build_lexicon.py` established.

    python scripts/build_lexicon.py [--lexique Lexique382.zip] [--dump PATH]

Lexique is CC BY-SA 4.0 and so is French Wiktionary. See LICENSE-LEXIQUE,
LICENSE-WIKTIONARY, and ADR 0032 for why Wikidata Lexemes could not serve here.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

LEXIQUE_URL = "http://www.lexique.org/databases/Lexique382/Lexique382.zip"
USER_AGENT = "denckring-fr-data/0.1 (https://github.com/senzelden/denckring)"

DATA = Path(__file__).resolve().parents[1] / "src" / "denckring_fr_data" / "data"
WORDS = DATA / "words.txt.gz"
NOUNS = DATA / "nouns.txt.gz"
GRADED = DATA / "graded_words.txt.gz"
METADATA = DATA / "metadata.json"

#: Six bands, and larger means *less* common — SCOWL's direction, which
#: `LanguagePack.graded_words` documents and `anagram` sorts ascending by.
#: Lexique's frequencies run the other way, so the build inverts rather than
#: leaking a source's convention into a capability's contract. Six rather than
#: SCOWL's finer set because Lexique gives a continuous frequency and any
#: bucketing of it is arbitrary; six is enough for a ranking and few enough to
#: eyeball. The ceiling is 60 because `anagram`'s `max_size` is capped there.
BANDS = (10, 20, 30, 40, 50, 60)


def lexique_rows(archive: Path) -> list[dict[str, str]]:
    """Every row of Lexique382.tsv."""
    with zipfile.ZipFile(archive) as bundle:
        raw = bundle.read("Lexique382.tsv").decode("utf-8")
    return list(csv.DictReader(io.StringIO(raw), delimiter="\t"))


def frequency(row: dict[str, str]) -> float:
    """The higher of the two corpora, so a word common in either is common.

    Books and film subtitles disagree sharply — `nonobstant` is bookish and
    `ouais` is not — and taking the max rather than the mean keeps a word that
    is common in one register from being ranked rare because it is absent from
    the other.
    """
    best = 0.0
    for column in ("freqlivres", "freqfilms2"):
        try:
            best = max(best, float(row[column].replace(",", ".")))
        except (KeyError, ValueError):
            continue
    return best


def build_tables(rows: list[dict[str, str]]) -> tuple[list[str], list[str], dict[str, int]]:
    """Word list, noun list and frequency bands, in that order."""
    best: dict[str, float] = {}
    nouns: set[str] = set()
    for row in rows:
        word = row["ortho"].strip()
        if not word or not word.replace("-", "").replace("'", "").isalpha():
            continue
        best[word] = max(best.get(word, 0.0), frequency(row))
        if row["cgram"] == "NOM":
            nouns.add(word)
    ranked = sorted(best, key=lambda w: (-best[w], w))
    bands = {
        word: BANDS[min(index * len(BANDS) // max(len(ranked), 1), len(BANDS) - 1)]
        for index, word in enumerate(ranked)
    }
    return sorted(best), sorted(nouns), bands


def _write_list(path: Path, items: list[str]) -> None:
    """One item per line, gzipped with a fixed mtime so rebuilds diff cleanly."""
    payload = "".join(f"{item}\n" for item in items).encode("utf-8")
    with gzip.GzipFile(path, "wb", mtime=0) as handle:
        handle.write(payload)


def _write_table(path: Path, table: dict[str, int]) -> None:
    payload = "".join(f"{k}\t{v}\n" for k, v in sorted(table.items())).encode("utf-8")
    with gzip.GzipFile(path, "wb", mtime=0) as handle:
        handle.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lexique", type=Path, help="A downloaded Lexique382.zip.")
    args = parser.parse_args()

    archive = args.lexique
    if archive is None:
        archive = DATA.parent.parent.parent / "Lexique382.zip"
        print(f"downloading {LEXIQUE_URL} -> {archive}", file=sys.stderr)
        request = urllib.request.Request(LEXIQUE_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request) as response, archive.open("wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)

    words, nouns, bands = build_tables(lexique_rows(archive))
    DATA.mkdir(parents=True, exist_ok=True)
    _write_list(WORDS, words)
    _write_list(NOUNS, nouns)
    _write_table(GRADED, bands)

    existing = json.loads(METADATA.read_text(encoding="utf-8")) if METADATA.exists() else {}
    counts = {
        **existing.get("counts", {}),
        WORDS.name: len(words),
        NOUNS.name: len(nouns),
        GRADED.name: len(bands),
    }
    METADATA.write_text(
        json.dumps(
            {
                "counts": counts,
                "generated": datetime.now(UTC).date().isoformat(),
                "source": (
                    "Lexique 3.82 (lexique.org), CC BY-SA 4.0, and French Wiktionary, "
                    "CC BY-SA 4.0 - see LICENSE-LEXIQUE, LICENSE-WIKTIONARY and "
                    "scripts/build_lexicon.py"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(words)} words, {len(nouns)} nouns, {len(bands)} bands", file=sys.stderr)


if __name__ == "__main__":
    main()
