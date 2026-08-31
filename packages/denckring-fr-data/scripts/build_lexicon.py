"""Regenerate the vendored French lexicon from Lexique 3.82 and a Wiktionary dump.

Committed so the data files are reproducible and diffable, the convention
`denckring-de-data/scripts/build_lexicon.py` established.

    python scripts/build_lexicon.py [--lexique Lexique382.zip] [--dump PATH]

Lexique is CC BY-SA 4.0 and so is French Wiktionary. See LICENSE-LEXIQUE,
LICENSE-WIKTIONARY, and ADR 0032 for why Wikidata Lexemes could not serve here.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import gzip
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

LEXIQUE_URL = "http://www.lexique.org/databases/Lexique382/Lexique382.zip"
#: Recorded for provenance and surfaced in `--dump`'s help text, but never fetched
#: automatically the way `--lexique`'s omission fetches `LEXIQUE_URL`. The German
#: sibling's equivalent dump is 267 MB; this one is 876 MB, and a flag omitted by
#: accident should not silently start an 876 MB download — the caller must pass
#: `--dump` and mean it.
DUMP_URL = (
    "https://dumps.wikimedia.org/frwiktionary/latest/frwiktionary-latest-pages-articles.xml.bz2"
)
USER_AGENT = "denckring-fr-data/0.1 (https://github.com/senzelden/denckring)"

DATA = Path(__file__).resolve().parents[1] / "src" / "denckring_fr_data" / "data"
WORDS = DATA / "words.txt.gz"
NOUNS = DATA / "nouns.txt.gz"
GRADED = DATA / "graded_words.txt.gz"
GLOSSES = DATA / "glosses.txt.gz"
METADATA = DATA / "metadata.json"

#: The dump's export schema version appears in every tag name. Read from the root
#: element rather than hardcoded, because Wikimedia bumps it.
_NS = re.compile(r"^\{([^}]+)\}")
#: A language section runs from its own heading to the next one.
_FRENCH = re.compile(r"^==\s*\{\{langue\|fr\}\}\s*==\s*$", re.M)
_ANY_LANGUAGE = re.compile(r"^==\s*\{\{langue\|[^}]+\}\}\s*==\s*$", re.M)
#: A sense is a `#` line. `#*` is an example sentence under one, and `#:` a
#: usage note; neither is a definition, hence the negative lookahead.
_SENSE = re.compile(r"^#\s+(?!\*)(.+)$", re.M)
#: A part-of-speech subsection inside a language section, e.g. `=== {{S|nom|fr}} ===`
#: or `=== {{S|verbe|fr|flexion}} ===`. The `flexion` argument marks an inflected
#: form rather than a headword's own entry: `accédons` under one reads "Première
#: personne du pluriel de l'indicatif présent du verbe accéder", which describes
#: the grammatical form rather than defining the word. `definitional_expansion` fed
#: that would replace a word with a description of its own inflection, so senses
#: are read subsection by subsection and any `flexion` subsection is skipped.
_POS_HEADER = re.compile(r"^=+\s*\{\{S\|([^}]*)\}\}\s*=+\s*$", re.M)

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
        # Rejects 310 of 125,653 distinct forms and 164 of 48,234 nouns, every
        # one a multi-word entry (`a priori`, `acid jazz`, `action painting`)
        # whose space fails `isalpha()`. Correct and desirable: the tokeniser
        # can never produce a multi-word form, so such an entry could never match.
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


def _namespace(path: Path) -> str:
    with bz2.open(path, "rb") as handle:
        for _, elem in ET.iterparse(handle, events=("start",)):
            match = _NS.match(elem.tag)
            return match.group(1) if match else ""
    return ""


def _strip_markup(raw: str) -> str:
    """Wiki markup to plain text, conservatively.

    Templates are dropped whole rather than expanded: expanding them needs the
    template namespace and a parser, and what they mostly carry in this position
    is domain labels and reference plumbing.
    """
    text = re.sub(r"\{\{[^{}]*\}\}", "", raw)
    text = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    return re.sub(r"\s+", " ", text).strip(" ;,")


def glosses_from(path: Path) -> Iterator[tuple[str, list[str]]]:
    """Every French headword in the dump with its definitions.

    Streaming, and clearing each element as it is consumed: the uncompressed dump
    is several gigabytes and holding it would need more memory than the machines
    this runs on have.
    """
    namespace = _namespace(path)
    tag = f"{{{namespace}}}" if namespace else ""
    with bz2.open(path, "rb") as handle:
        for _, elem in ET.iterparse(handle, events=("end",)):
            if elem.tag != f"{tag}page":
                continue
            page_namespace = elem.findtext(f"{tag}ns")
            title = elem.findtext(f"{tag}title") or ""
            wikitext = elem.findtext(f"{tag}revision/{tag}text") or ""
            elem.clear()
            # Namespace 0 only: `Annexe:`, `Thésaurus:` and `Conjugaison:` pages
            # are apparatus over entries rather than entries.
            if page_namespace != "0" or not title or not wikitext:
                continue
            start = _FRENCH.search(wikitext)
            if start is None:
                continue
            following = _ANY_LANGUAGE.search(wikitext, start.end())
            section = wikitext[start.end() : following.start() if following else len(wikitext)]
            # Senses are read subsection by subsection, not from the language
            # section as a whole, so a `flexion` subsection's inflection notes
            # (see `_POS_HEADER`) can be skipped without also losing the etymology
            # or pronunciation subsections' surrounding text.
            senses: list[str] = []
            headers = list(_POS_HEADER.finditer(section))
            for index, header in enumerate(headers):
                if "flexion" in header.group(1).split("|"):
                    continue
                chunk_end = headers[index + 1].start() if index + 1 < len(headers) else len(section)
                chunk = section[header.end() : chunk_end]
                senses += [s for s in (_strip_markup(m) for m in _SENSE.findall(chunk)) if s]
            # `" | "` is the separator downstream, so a sense containing it is
            # dropped rather than escaped: splitting must be unambiguous, and
            # `denckring-en-data` and `denckring-de-wiktionary` both split this way.
            usable = [s for s in dict.fromkeys(senses) if " | " not in s and "\t" not in s]
            if usable:
                yield title, usable


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
    parser.add_argument("--dump", type=Path, help=f"A downloaded frwiktionary dump ({DUMP_URL}).")
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

    if args.dump is not None:
        rendered = [(title, " | ".join(senses)) for title, senses in glosses_from(args.dump)]
        payload = "".join(f"{k}\t{v}\n" for k, v in rendered).encode("utf-8")
        with gzip.GzipFile(GLOSSES, "wb", mtime=0) as handle:
            handle.write(payload)
        counts[GLOSSES.name] = len(rendered)
        print(f"{len(rendered)} glosses", file=sys.stderr)

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
