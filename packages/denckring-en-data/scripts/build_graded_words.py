"""Regenerate the vendored graded English word list from SCOWL.

Committed so the data file is reproducible and diffable, and so neither
installation nor use touches the network (ADR 0013).

    python scripts/build_graded_words.py [scowl-2020.12.07.tar.gz]

SCOWL is MIT-like: no share-alike, no non-commercial clause. It is derived from
several sources with their own terms, and UKACD's requires its notice be
reproduced verbatim - which is why LICENSE-SCOWL is SCOWL's whole Copyright file
rather than a summary of it. See LICENSE-SCOWL.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

#: Pinned, not "latest": the shipped band of every word is part of this package's
#: observable behaviour, so an unpinned build would silently reorder anagram
#: results between releases.
RELEASE = "2020.12.07"
URL = f"https://downloads.sourceforge.net/project/wordlist/SCOWL/{RELEASE}/scowl-{RELEASE}.tar.gz"
USER_AGENT = "denckring-en-data/0.1 (https://github.com/senzelden/denckring)"

#: Only `*-words.*`. SCOWL also ships `*-proper-names.*` and `*-abbreviations.*`,
#: and those are precisely the defect being fixed: `sutphen`, `dority` and
#: `romito` are why the existing `known_words()` oracle cannot tell `room` from
#: `romito`. A general word list that readmits surnames would have bought nothing.
WANTED = re.compile(r"^(english|american)-words\.(\d+)$")

#: 60 is where the shipped list stops, and the number is SCOWL's own: its
#: documentation calls 60 "the largest size that I am fairly confident does not
#: contain any misspellings or invalid words". A search over the shipped list may
#: draw a narrower line than 60; nothing above it ships, so nothing can ask for more.
MAX_BAND = 60

#: SCOWL's files are Latin-1, not UTF-8.
ENCODING = "iso-8859-1"

#: One alphabetic ASCII token, two letters or more. `noun_list()` restricts to
#: alphabetic lemmas for the reason that applies here too - a cover made of
#: `cat's-paw` cannot survive the tokeniser that reads the result back - and this
#: adds two restrictions of its own. Accented forms (157 of them, `abbé` and
#: friends) can only ever cover a source word carrying the same accent, which a
#: folded input never does. Single letters would be worse than useless: all 26
#: appear at low bands, so admitting them lets any input at all be "covered" by
#: letter salad. The cost is real and is `a` and `I`, which are words.
TOKEN = re.compile(r"[a-z]{2,}")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "denckring_en_data" / "data"
#: Shared with build_lexicon.py, which writes the WordNet half of it. Both merge
#: rather than replace, so neither script drops the other's provenance.
METADATA = DATA / "metadata.json"
LICENCE = ROOT / "LICENSE-SCOWL"

#: Provenance clauses in `metadata.json`'s `source` are joined with "; " and
#: keyed by their first word, so re-running a build replaces its own clause
#: instead of appending a second copy of it.
SEPARATOR = "; "
KEY = "SCOWL"


def download(destination: Path) -> None:
    """Fetch the pinned release. Run by hand: ADR 0013 puts the network in the
    build, never in installation or use, which is why the output is committed."""
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def read_bands(tar: tarfile.TarFile) -> tuple[dict[str, int], list[int]]:
    """Word to its lowest SCOWL size, plus every size this release ships.

    Lowest, not first seen or last seen: a word appears in every size at or
    above the one it enters at, and the smallest list containing it is the
    strongest statement of its commonness.
    """
    table: dict[str, int] = {}
    sizes: set[int] = set()
    for member in tar.getmembers():
        path = PurePosixPath(member.name)
        matched = WANTED.match(path.name)
        if matched is None or path.parent.name != "final":
            continue
        band = int(matched.group(2))
        sizes.add(band)
        if band > MAX_BAND:
            continue
        handle = tar.extractfile(member)
        if handle is None:
            continue
        for line in handle.read().decode(ENCODING).splitlines():
            word = line.strip().casefold()
            if TOKEN.fullmatch(word) and band < table.get(word, MAX_BAND + 1):
                table[word] = band
    return table, sorted(sizes)


def write_licence(tar: tarfile.TarFile) -> None:
    """Copy SCOWL's Copyright file out of the release, verbatim and whole.

    Whole, not trimmed to the sources this build actually draws on. UKACD enters
    SCOWL at the 80 level only, so its term that the notice be reproduced
    verbatim is not triggered by a build capped at 60 - but a licence excerpted
    to what applies today is how a package acquires a defect the next time the
    cap moves.
    """
    for member in tar.getmembers():
        path = PurePosixPath(member.name)
        if path.name == "Copyright" and len(path.parts) == 2:
            handle = tar.extractfile(member)
            if handle is None:
                break
            LICENCE.write_bytes(handle.read())
            print(f"  {LICENCE.name}: {LICENCE.stat().st_size:,} bytes", file=sys.stderr)
            return
    raise RuntimeError(f"no Copyright file in {URL}")


def write_gz(path: Path, table: Mapping[str, int]) -> int:
    """One `word\\tband` line per entry, sorted by word."""
    entries = [f"{word}\t{band}" for word, band in sorted(table.items())]
    payload = "\n".join(entries).encode("utf-8")
    # mtime=0: gzip embeds a timestamp by default, so two runs over identical
    # content would otherwise produce different bytes and `git diff` would
    # show "Binary files differ" even when nothing changed.
    path.write_bytes(gzip.compress(payload, mtime=0))
    print(
        f"  {path.name}: {len(entries):,} entries, {path.stat().st_size:,} bytes", file=sys.stderr
    )
    return len(entries)


def merge_source(existing: str, clause: str) -> str:
    """Replace this script's clause in `source`, leaving the other script's."""
    # A clause may not contain the separator. One that did would be split into a
    # fragment nothing can key, and that fragment would then survive every later
    # run - which is what the first draft of this script actually did.
    assert SEPARATOR not in clause
    kept = [part for part in existing.split(SEPARATOR) if part and not part.startswith(f"{KEY} ")]
    return SEPARATOR.join([*kept, clause])


def write_metadata(count: int, sizes: list[int]) -> None:
    """Record the entry count beside the WordNet ones, so a test can assert the
    shipped file still matches and a silent corpus change fails loudly.

    The sizes are recorded because SCOWL's numbering has moved: v2 tops out at
    85 and ships no 95 at all, while this release ships 95 - its README calls it
    "insane" - and no 85. Anything written against v2's numbering does not
    describe this data. The build's own date lives in the clause rather than in
    the top-level `generated`, which belongs to build_lexicon.py's files.
    """
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    clause = (
        f"{KEY} {RELEASE} (sizes {' '.join(str(size) for size in sizes)}, "
        f"vendored up to {MAX_BAND}), generated "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')} - see LICENSE-SCOWL and "
        f"scripts/{Path(__file__).name}"
    )
    metadata["counts"]["graded_words.txt.gz"] = count
    metadata["source"] = merge_source(metadata["source"], clause)
    METADATA.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  {METADATA.name}: {metadata}", file=sys.stderr)


def main(argv: list[str]) -> int:
    # An already-downloaded tarball may be passed as the single argument. The
    # build is identical either way; the fetch is just the slow, flaky part of a
    # by-hand run, and nothing but this script ever reads a local copy.
    with tempfile.TemporaryDirectory() as workspace:
        archive = Path(argv[1]) if len(argv) > 1 else Path(workspace) / "scowl.tar.gz"
        if len(argv) <= 1:
            download(archive)
        with tarfile.open(archive) as tar:
            table, sizes = read_bands(tar)
            write_licence(tar)
    write_metadata(write_gz(DATA / "graded_words.txt.gz", table), sizes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
