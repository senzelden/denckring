"""Build English word frequencies from a Leipzig Corpora Collection corpus.

Run by hand, not by any gate. It downloads 288 MB and writes one artefact:

    uv run python packages/denckring-en-data/scripts/build_frequencies.py \
        [--expected-sha256 HASH]

The source is the Leipzig Corpora Collection's `eng_news_2023_1M`, whose
`*-words.txt` is `id <tab> word <tab> frequency`. Only that one member is read;
the sentences, the source list and the two co-occurrence tables are never opened
and never redistributed. See ADR 0052, and `LICENSE-LEIPZIG` for attribution.

Leipzig's terms forbid automated *queries* against their web service. This is
the published download they offer instead, taken once and cached.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import tarfile
import urllib.request
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path

from _download_integrity import verify_or_record

CORPUS = "eng_news_2023_1M"
URL = f"https://downloads.wortschatz-leipzig.de/corpora/{CORPUS}.tar.gz"
#: Captured 2026-10-04 from a real download of the URL above — 287,898,033
#: bytes. Re-run this script with `--expected-sha256 ''` to print a new digest to
#: pin if the corpus is ever replaced at this URL.
EXPECTED_SHA256: str | None = "c8a5a5e72897aa5e367b0319c1884831c02aaf29bf81342de31ca1b1cc8f3e4c"

#: Where the German chapters already cache their downloads.
CACHE = Path.home() / ".cache" / "denckring-dumps"


def counts(rows: Iterable[tuple[str, int]], graded: Mapping[str, int]) -> dict[str, int]:
    """Corpus rows to a word-to-count table over the graded vocabulary.

    **The case rule (ADR 0052).** A form counts only as written in lowercase.
    English capitals mark a sentence's start or a name, and news is full of
    names: counting `Trump`, `Bush` or `Bill` as `trump`, `bush` and `bill` would
    rank those common nouns by last year's headlines. The cost is the other
    capital, a common word opening a sentence (`However`), whose count is
    undercounted by the share of its uses that open one; ranking among words
    is what the table is for, and that share is similar across most words.

    Kept to `graded`'s keys, SCOWL's sizes up to 60, which carry no names, no
    abbreviations and no misspellings, so the table ranks the words the pack
    already calls words and adds none. `rows` may repeat a form; the largest
    count wins, which reads a duplicated row once where a sum would count it
    twice. A form the corpus split across rows would want the sum instead.
    """
    best: dict[str, int] = {}
    for form, count in rows:
        if form in graded and form.islower():
            best[form] = max(best.get(form, 0), count)
    return best


def fetch(cache: Path = CACHE, *, expected_sha256: str | None) -> Path:
    """The corpus archive, downloaded once and kept, hashed either way (P2-05)."""
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{CORPUS}.tar.gz"
    cached = archive.exists()
    if cached:
        data = archive.read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=600) as response:
            data = response.read()
    # Hash before writing, so a mismatch never reaches the cache.
    digest = verify_or_record(data, source=URL, expected_sha256=expected_sha256)
    print(f"{URL}: sha256 {digest}", file=sys.stderr)
    if not cached:
        archive.write_bytes(data)
    return archive


def rows_from(archive: Path) -> list[tuple[str, int]]:
    """The `(form, count)` pairs from the archive's one words file, read in place."""
    wanted = f"{CORPUS}/{CORPUS}-words.txt"
    with tarfile.open(archive) as bundle:
        member = bundle.extractfile(wanted)
        if member is None:
            raise SystemExit(f"{wanted} is not in {archive}")
        rows: list[tuple[str, int]] = []
        for line in member.read().decode("utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2].isdigit():
                rows.append((parts[1], int(parts[2])))
    return rows


def main() -> None:
    from denckring_en_data import graded_words

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-sha256",
        help="SHA-256 the corpus archive must match (defaults to EXPECTED_SHA256).",
    )
    args = parser.parse_args()
    expected = args.expected_sha256 if args.expected_sha256 is not None else EXPECTED_SHA256

    archive = fetch(expected_sha256=expected or None)
    rows = rows_from(archive)
    table = counts(rows, graded_words())
    data = Path(__file__).parent.parent / "src" / "denckring_en_data" / "data"
    out = data / "frequencies.txt.gz"
    # `mtime=0` so a rebuild from the same corpus writes the same bytes.
    with (
        open(out, "wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed,
    ):
        for word in sorted(table):
            packed.write(f"{word}\t{table[word]}\n".encode())
    metadata_path = data / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["counts"]["frequencies.txt.gz"] = len(table)
    metadata["frequency"] = {
        "corpus": CORPUS,
        "generated": date.today().isoformat(),
        "rows_read": len(rows),
        "source": (
            "Leipzig Corpora Collection, CC BY 4.0 - see LICENSE-LEIPZIG, NOTICE on the "
            "licence version, and scripts/build_frequencies.py"
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"{len(rows)} rows in, {len(table)} words counted, {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
