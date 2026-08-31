"""Regenerate the vendored German pronunciations and glosses from a Wiktionary dump.

Committed so the data files are reproducible and diffable, the same convention
`denckring-de-data/scripts/build_lexicon.py` follows.

    python scripts/build_pronunciations.py [--dump PATH]

Without `--dump` the current `dewiktionary-latest-pages-articles.xml.bz2` is
downloaded to a temporary file, which is roughly 270MB. With it, an already
downloaded copy is read instead — the dump is regenerated weekly and pinning a
local copy is the only way to reproduce a past build exactly.

German Wiktionary is CC BY-SA 4.0. See LICENSE-WIKTIONARY, and ADR 0030 for why
that licence is quarantined in a distribution of its own.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

DUMP_URL = (
    "https://dumps.wikimedia.org/dewiktionary/latest/dewiktionary-latest-pages-articles.xml.bz2"
)
USER_AGENT = "denckring-de-wiktionary/0.1 (https://github.com/senzelden/denckring)"

DATA = Path(__file__).resolve().parents[1] / "src" / "denckring_de_wiktionary" / "data"
PRONUNCIATIONS = DATA / "pronunciations.txt.gz"
GLOSSES = DATA / "glosses.txt.gz"
#: Beside the .gz files: the generation date and the entry counts, so a silent
#: corpus change fails a test loudly instead of drifting unnoticed. Same reason
#: `denckring-de-data` carries one.
METADATA = DATA / "metadata.json"

#: The dump's export schema version appears in every tag name. Read from the
#: root element rather than hardcoded, because Wikimedia bumps it.
_NS = re.compile(r"^\{([^}]+)\}")

#: A language section runs from its own heading to the next one. Matching the
#: heading rather than the `{{Sprache|Deutsch}}` template alone matters: a
#: French entry citing German in its etymology is not a German entry.
_GERMAN = re.compile(r"^==\s*[^=]*\(\{\{Sprache\|Deutsch\}\}\)\s*==\s*$", re.M)
_ANY_LANGUAGE = re.compile(r"^==\s*[^=]*\(\{\{Sprache\|[^}]+\}\}\)\s*==\s*$", re.M)
#: Only transcriptions on an `{{IPA}}` line. `{{Lautschrift}}` also appears under
#: `{{Reime}}` and in etymologies, where it transcribes something other than the
#: headword.
_IPA_LINE = re.compile(r"^:\{\{IPA\}\}(.*)$", re.M)
_LAUTSCHRIFT = re.compile(r"\{\{Lautschrift\|([^}|]*)\}\}")
_BEDEUTUNGEN = re.compile(r"^\{\{Bedeutungen\}\}\s*$(.*?)(?=^\{\{|\Z)", re.M | re.S)
_SENSE = re.compile(r"^:\[[^\]]*\]\s*(.+)$", re.M)

#: Every symbol a standard German transcription is built from, plus the four
#: loan symbols that survive in words German has borrowed whole (`θ`, `ð`, `w`,
#: `ɹ` in English loans; `ʒ` and `ɑ̃` in French ones).
#:
#: The set is a filter, not documentation: a transcription containing anything
#: outside it is dropped rather than repaired. What that excludes is mostly not
#: German — multi-word phrase entries, which carry a space; placeholder
#: transcriptions written `…`; and a long tail of one-off symbols from
#: dialect notes and IPA for other languages. Dropping them keeps a promise the
#: pack makes downstream, that a phoneme list is a list of German phonemes.
_ALLOWED = frozenset(
    "abcdefhijklmnoprstuvxyz"  # base Latin letters used as IPA symbols
    "ɐɑæðøœɛəɔɒʌɜ"  # vowels
    "ɪʊʏ"  # lax vowels
    "ɡŋʁʃʒçʔθɹ"  # consonants
    "ˈˌː"  # stress and length
    "͡"  # tie bar, joining an affricate: t͡s
    "̯"  # inverted breve below, the glide of a diphthong: aɪ̯
    "̩̍"  # vertical line below/above, a syllabic consonant: n̩, ŋ̍
    "̃"  # tilde, a nasal vowel: ɛ̃
    "̥"  # ring below, a devoiced consonant: ʁ̥
    "̧"  # cedilla, which NFD splits ç into
)


def _namespace(path: Path) -> str:
    with bz2.open(path, "rb") as handle:
        for _, elem in ET.iterparse(handle, events=("start",)):
            match = _NS.match(elem.tag)
            return match.group(1) if match else ""
    return ""


def _german_section(text: str) -> str | None:
    start = _GERMAN.search(text)
    if start is None:
        return None
    following = _ANY_LANGUAGE.search(text, start.end())
    return text[start.end() : following.start() if following else len(text)]


def _clean_ipa(raw: str) -> str | None:
    """One transcription, normalised, or None if it is not usable German IPA."""
    form = unicodedata.normalize("NFC", raw).strip()
    if not form:
        return None
    if any(ch not in _ALLOWED for ch in unicodedata.normalize("NFD", form)):
        return None
    return form


def _strip_markup(raw: str) -> str:
    """Wiki markup to plain text, conservatively.

    Templates are dropped whole rather than expanded: expanding them needs the
    template namespace and a parser, and what they mostly carry in this position
    is reference plumbing. A gloss reduced to nothing by that is discarded.
    """
    text = re.sub(r"\{\{[^{}]*\}\}", "", raw)
    text = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ;,")


def entries(path: Path) -> Iterator[tuple[str, list[str], list[str]]]:
    """Every German headword in the dump with its transcriptions and glosses.

    Streaming, and clearing each element as it is consumed: the uncompressed
    dump is several gigabytes and holding it would need more memory than the
    machines this runs on have.
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
            # Namespace 0 only: `Verzeichnis:`, `Reim:` and `Flexion:` pages are
            # indexes over entries rather than entries.
            if page_namespace != "0" or not title or not wikitext:
                continue
            section = _german_section(wikitext)
            if section is None:
                continue
            forms: list[str] = []
            for line in _IPA_LINE.findall(section):
                forms += [f for f in (_clean_ipa(m) for m in _LAUTSCHRIFT.findall(line)) if f]
            senses: list[str] = []
            block = _BEDEUTUNGEN.search(section)
            if block:
                found = (_strip_markup(m) for m in _SENSE.findall(block.group(1)))
                senses = [sense for sense in found if sense]
            # `dict.fromkeys` rather than a set: the order Wiktionary lists them
            # in is the order the pack reports, and the first form is the one
            # `rhyme_key` and `stress_pattern` answer with.
            yield title, list(dict.fromkeys(forms)), list(dict.fromkeys(senses))


def _write(path: Path, rows: list[tuple[str, str]]) -> None:
    """One `key\\tvalue` line per row, gzipped with a fixed mtime.

    `mtime=0` so two builds of the same dump produce byte-identical files; a
    timestamp in the gzip header would make every rebuild a diff.
    """
    payload = "".join(f"{key}\t{value}\n" for key, value in rows).encode("utf-8")
    with gzip.GzipFile(path, "wb", mtime=0) as handle:
        handle.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, help="A downloaded dewiktionary dump to read.")
    args = parser.parse_args()

    dump = args.dump
    if dump is None:
        dump = DATA.parent.parent.parent / "dewiktionary-latest-pages-articles.xml.bz2"
        print(f"downloading {DUMP_URL} -> {dump}", file=sys.stderr)
        request = urllib.request.Request(DUMP_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request) as response, dump.open("wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)

    pronunciations: list[tuple[str, str]] = []
    glosses: list[tuple[str, str]] = []
    for title, forms, senses in entries(dump):
        if forms:
            pronunciations.append((title, "|".join(forms)))
        if senses:
            # `" | "` as the separator, and senses containing it are rejected
            # rather than escaped, because splitting on it downstream must be
            # unambiguous. `denckring-en-data` splits its glosses the same way.
            usable = [s for s in senses if " | " not in s and "\t" not in s]
            if usable:
                glosses.append((title, " | ".join(usable)))

    DATA.mkdir(parents=True, exist_ok=True)
    _write(PRONUNCIATIONS, pronunciations)
    _write(GLOSSES, glosses)
    METADATA.write_text(
        json.dumps(
            {
                "counts": {
                    PRONUNCIATIONS.name: len(pronunciations),
                    GLOSSES.name: len(glosses),
                },
                "generated": datetime.now(UTC).date().isoformat(),
                "source": (
                    "German Wiktionary (dewiktionary-latest-pages-articles), CC BY-SA 4.0 - "
                    "see LICENSE-WIKTIONARY and scripts/build_pronunciations.py"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(pronunciations)} pronunciations, {len(glosses)} glosses", file=sys.stderr)


if __name__ == "__main__":
    main()
