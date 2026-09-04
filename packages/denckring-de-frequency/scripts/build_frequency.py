"""Build German frequency bands from a Leipzig Corpora Collection corpus.

Run by hand, not by any gate. It downloads 219 MB and writes one artefact:

    uv run python packages/denckring-de-frequency/scripts/build_frequency.py

The source is the Leipzig Corpora Collection's `deu_news_2023_1M`, whose
`*-words.txt` is `id <tab> word <tab> frequency`. Only that one member is read;
the sentences, the source list and the two co-occurrence tables are never opened
and never redistributed. See ADR 0038, and `LICENSE-LEIPZIG` for attribution.

Leipzig's terms forbid automated *queries* against their web service. This is
the published download they offer instead, taken once and cached.
"""

from __future__ import annotations

import gzip
import json
import tarfile
import urllib.request
from datetime import date
from pathlib import Path

CORPUS = "deu_news_2023_1M"
URL = f"https://downloads.wortschatz-leipzig.de/corpora/{CORPUS}.tar.gz"

#: Where the German Wiktionary chapter already caches its dump.
CACHE = Path.home() / ".cache" / "denckring-dumps"

#: Six bands, larger meaning *less* common — SCOWL's direction, which
#: `LanguagePack.graded_words` documents and `anagram` sorts ascending by. The
#: ceiling is 60 because `anagram`'s `max_size` is capped there. Identical to
#: `denckring-fr-data`'s, deliberately: this is the third distribution to write
#: the same split, and re-deriving it would be a third chance to invert it.
BANDS = (10, 20, 30, 40, 50, 60)

#: `cd`, `kg` and `PS` are unit symbols and abbreviations rather than words worth
#: ranking. The same floor `calculator_word` chose, for the same reason.
MIN_LENGTH = 3


def bands(rows: list[tuple[str, int]], known: set[str], nouns_lower: set[str]) -> dict[str, int]:
    """Frequency rows to a word-to-band table, applying the case rule.

    **ADR 0038 D3, and the decision this whole chapter turns on.** German
    capitalises common nouns, so a noun's German tokens are capitalised and its
    lowercase tokens belong to another language. Leipzig keeps that distinction.
    This project's own German word lists have thrown it away — `known_words()`
    is 0 capitalised of 668,580 — and only `nouns()` keeps it, so the noun list
    is the case oracle:

    - a form whose lowercase is a known noun counts **only when capitalised**;
    - every other form counts only when lowercase.

    Lowercase `power`, `list` and `tower` in a German corpus are English tokens
    and are dropped; their capitalised German counterparts are kept with the
    frequency they actually have.

    Without this the chapter reverts to the failure it exists to fix. The
    rejected OpenSubtitles source had lowercased everything, merging `Tag` with
    `tag`; a later draft here then lowercased the Leipzig keys *before*
    intersecting and reproduced the same defect from the other end —
    `Wortspiel -> list power` came straight back at 1M scale, where lowercase
    English `list` does occur in German news.

    `rows` may repeat a form; the largest count wins, since a corpus can split
    one word across rows the tokeniser did not unify.
    """
    best: dict[str, int] = {}
    for form, count in rows:
        if not form.isalpha() or len(form) < MIN_LENGTH:
            continue
        low = form.lower()
        if low not in known:
            continue
        if (low in nouns_lower) != form[:1].isupper():
            continue
        best[low] = max(best.get(low, 0), count)

    ranked = sorted(best, key=lambda word: (-best[word], word))
    return {
        word: BANDS[min(index * len(BANDS) // max(len(ranked), 1), len(BANDS) - 1)]
        for index, word in enumerate(ranked)
    }


def fetch(cache: Path = CACHE) -> Path:
    """The corpus archive, downloaded once and kept."""
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{CORPUS}.tar.gz"
    if not archive.exists():
        urllib.request.urlretrieve(URL, archive)
    return archive


def rows_from(archive: Path) -> list[tuple[str, int]]:
    """The `(form, count)` pairs from the archive's one words file.

    Read straight out of the tar rather than unpacking: the archive also holds a
    million sentences, a source list and two co-occurrence tables that this build
    never wants and that would cost about a gigabyte on disk to ignore.
    """
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
    from denckring_de_data import GermanDataPack, known_words

    archive = fetch()
    rows = rows_from(archive)
    table = bands(
        rows,
        {word.lower() for word in known_words()},
        {noun.lower() for noun in GermanDataPack().nouns()},
    )
    data = Path(__file__).parent.parent / "src" / "denckring_de_frequency" / "data"
    out = data / "graded_words.txt.gz"
    with gzip.open(out, "wt", encoding="utf-8") as handle:
        for word in sorted(table):
            handle.write(f"{word}\t{table[word]}\n")
    # `rows_read` is not in the German lexical package's metadata and is here on
    # purpose: the ratio of rows in to words out is what the case rule changes,
    # so a rebuild that quietly lost the rule shows up as the same corpus
    # suddenly yielding far more words.
    (data / "metadata.json").write_text(
        json.dumps(
            {
                "counts": {"graded_words.txt.gz": len(table)},
                "generated": date.today().isoformat(),
                "rows_read": len(rows),
                "corpus": CORPUS,
                "source": (
                    "Leipzig Corpora Collection, CC BY - see LICENSE-LEIPZIG, "
                    "NOTICE on the licence version, and scripts/build_frequency.py"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(rows)} rows in, {len(table)} graded words, {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
