"""Regenerate the vendored English lexicon from the Open English WordNet.

Committed so the data files are reproducible and diffable, and so `nouns.txt`
has a script behind it: the vendored list this replaces was hand-extracted
from Princeton WordNet 3.1's `index.noun` and committed with no script,
which is why nobody could establish its provenance without reading a licence
file. `metadata.json`, written below, records the source and version so that
never happens again.

    uv run --group lexicon python scripts/build_lexicon.py

Open English WordNet 2024 is CC BY 4.0: attribution required, no
share-alike. See LICENSE-WORDNET.
"""

from __future__ import annotations

import gzip
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import wn

LEXICON_SPECIFIER = "oewn:2024"

DATA = Path(__file__).resolve().parents[1] / "src" / "denckring_en_data" / "data"
#: Beside the data files: the generation date, the WordNet version, and the
#: two entry counts, so a silent corpus change (a truncated download, a bad
#: regeneration) fails a test loudly instead of drifting unnoticed.
METADATA = DATA / "metadata.json"

#: Provenance clauses in `metadata.json`'s `source` are joined with "; " and
#: keyed by their leading label. build_graded_words.py writes the SCOWL clause
#: into the same file, so this script merges rather than replacing: a rewrite
#: here would drop the other's provenance and its entry count with it.
SEPARATOR = "; "


def single_word_alpha_lemmas() -> dict[str, list[wn.Word]]:
    """Every lemma across all parts of speech, lowercased, restricted to
    single alphabetic words, mapped to the `wn.Word` entries that produced it.

    Not noun-only: `nouns.txt` is filtered from this by part of speech below,
    but `glosses.txt.gz` covers every lemma the lexicon knows a definition
    for, the same way CMUdict is not noun-only either.
    """
    lexicon = wn.Wordnet(LEXICON_SPECIFIER)
    by_lemma: dict[str, list[wn.Word]] = {}
    for word in lexicon.words():
        lemma = word.lemma()
        if lemma.isalpha():
            by_lemma.setdefault(lemma.lower(), []).append(word)
    return by_lemma


def build_nouns() -> list[str]:
    """Every alphabetic single-word noun lemma, lowercased, deduplicated,
    sorted. This matches what the vendored list contained.

    Order is the point: N+7 and S+7 walk this list, so a noun's position has
    to be well defined and stable across regenerations - hence the plain
    `sorted()`, not insertion order from the database.
    """
    lexicon = wn.Wordnet(LEXICON_SPECIFIER)
    lemmas = {word.lemma().lower() for word in lexicon.words(pos="n") if word.lemma().isalpha()}
    return sorted(lemmas)


def build_glosses(by_lemma: dict[str, list[wn.Word]]) -> list[str]:
    """One line per lemma: `lemma\\tgloss | gloss | gloss`, one gloss per
    sense, across every part of speech and every homograph of that lemma.
    Sorted by lemma."""
    lines: list[str] = []
    for lemma in sorted(by_lemma):
        glosses = [
            sense.synset().definition() for word in by_lemma[lemma] for sense in word.senses()
        ]
        glosses = [g for g in glosses if g]
        lines.append(f"{lemma}\t{' | '.join(glosses)}")
    return lines


def write_text(path: Path, entries: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(entries) + "\n", encoding="utf-8")
    print(f"  {path.name}: {len(entries):,} entries", file=sys.stderr)
    return len(entries)


def write_gz(path: Path, entries: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(entries).encode("utf-8")
    # mtime=0: gzip embeds a timestamp by default, so two runs over identical
    # content would otherwise produce different bytes and `git diff` would
    # show "Binary files differ" even when nothing changed.
    path.write_bytes(gzip.compress(payload, mtime=0))
    print(f"  {path.name}: {len(entries):,} entries", file=sys.stderr)
    return len(entries)


def write_metadata(noun_count: int, gloss_count: int) -> None:
    """Record beside the data files what generated them, from what source,
    and how many entries they hold, so a test can assert the shipped files
    still match and a silent corpus change fails loudly instead of drifting."""
    lexicon = wn.lexicons(lexicon=LEXICON_SPECIFIER)[0]
    # Named, not "this script": two scripts write this file now, so "this" no
    # longer identifies one of them.
    clause = (
        f"{lexicon.label} {lexicon.version} ({LEXICON_SPECIFIER}), "
        f"{lexicon.license} - see LICENSE-WORDNET and scripts/{Path(__file__).name}"
    )
    metadata = json.loads(METADATA.read_text(encoding="utf-8")) if METADATA.exists() else {}
    kept = [
        part
        for part in metadata.get("source", "").split(SEPARATOR)
        if part and not part.startswith(f"{lexicon.label} ")
    ]
    metadata["generated"] = datetime.now(UTC).strftime("%Y-%m-%d")
    metadata["source"] = SEPARATOR.join([*kept, clause])
    metadata.setdefault("counts", {}).update(
        {"nouns.txt": noun_count, "glosses.txt.gz": gloss_count}
    )
    METADATA.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  {METADATA.name}: {metadata}")


def main() -> int:
    wn.download(LEXICON_SPECIFIER)

    nouns = build_nouns()
    noun_count = write_text(DATA / "nouns.txt", nouns)

    by_lemma = single_word_alpha_lemmas()
    gloss_lines = build_glosses(by_lemma)
    gloss_count = write_gz(DATA / "glosses.txt.gz", gloss_lines)

    write_metadata(noun_count, gloss_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
