# French, tranche A — the lexicon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the French pack `lexicon.words`, `lexicon.nouns`, `lexicon.glosses` and `lexicon.graded_words`, taking French from 70 of 121 runnable rows to 80, and making `anagram` generate in French.

**Architecture:** One new workspace distribution, `denckring-fr-data`, vendoring two CC BY-SA sources: Lexique 3.82 (a 142,694-row TSV) for word membership, nouns and frequency bands, and a glosses slice of the `frwiktionary` dump. It registers the `fr` entry point directly — no `pack()` factory, because unlike German there is no CC0 predecessor to quarantine data from. `FrenchDataPack` subclasses the core `FrenchPack` exactly as `GermanDataPack` subclasses `GermanPack`.

**Tech Stack:** Python 3.11+, hatchling, pydantic (unused here), uv workspaces, pytest, mypy --strict, ruff.

**Spec:** `docs/superpowers/specs/2026-08-31-french-design.md`

## Global Constraints

- **The gate is four commands and they must all be green:** `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`, `uv run ruff format --check .`. For anything touching a procedure also `uv run denckring eval --all` and `uv run denckring status`.
- **CI type-checks the packages and the four-command gate does not.** Anything touching a distribution must also pass `uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src packages/denckring-de-wiktionary/src packages/denckring-fr-data/src`.
- **Line length 100.** `ruff format` decides; do not hand-wrap against it.
- **Commit author is `senzelden <sunless@gmx.net>`.** The trailer is `Assisted-by: Claude:claude-opus-5[1m]`, never `Co-Authored-By:`, never `Signed-off-by:`, never a `Claude-Session:` trailer.
- **Do not push.** `origin/main` is pinned by decision; commit freely, push nothing.
- **Comments explain why, not what, and cite ADRs by number.** A comment that has become false is a defect, not a nit.
- **Provenance is recorded, never invented.** A claim of `author-stated` must cite a source with a year; record what is verified and mark what is not.
- **`procedure_id` is a reserved test-argument name** — `tests/conftest.py` auto-parametrises any test taking it. Name the argument `pid`.
- **Version-lock:** every distribution pins `denckring==0.1.0`. This makes a five-way lockstep.
- **Licence:** both sources are CC BY-SA 4.0. Attribution and share-alike are live obligations; the licence files must say so.

## Data sources, exactly

- **Lexique 3.82** — `http://www.lexique.org/databases/Lexique382/Lexique382.zip`, 26 MB, containing `Lexique382.tsv` (142,694 rows, 35 columns, tab-separated, UTF-8, header row). Columns used: `ortho`, `lemme`, `cgram`, `freqlivres`, `freqfilms2`. CC BY-SA 4.0, stated in the bundled `README-Lexique.txt`.
- **frwiktionary** — `https://dumps.wikimedia.org/frwiktionary/latest/frwiktionary-latest-pages-articles.xml.bz2`, 875,956,556 bytes. Used only for `lexicon.glosses` in this tranche.

## File Structure

| File | Responsibility |
|---|---|
| `packages/denckring-fr-data/pyproject.toml` | Distribution metadata, the `fr` entry point |
| `packages/denckring-fr-data/LICENSE` | Apache-2.0, copied from `denckring-de-data/LICENSE` |
| `packages/denckring-fr-data/LICENSE-LEXIQUE` | CC BY-SA 4.0 provenance for Lexique |
| `packages/denckring-fr-data/LICENSE-WIKTIONARY` | CC BY-SA 4.0 provenance for the glosses |
| `packages/denckring-fr-data/NOTICE` | What is Apache and what is CC BY-SA |
| `packages/denckring-fr-data/README.md` | What installing it gives, and the licence difference |
| `packages/denckring-fr-data/scripts/build_lexicon.py` | Both sources → four vendored files |
| `packages/denckring-fr-data/src/denckring_fr_data/__init__.py` | Table readers and `FrenchDataPack` |
| `packages/denckring-fr-data/src/denckring_fr_data/py.typed` | Empty marker |
| `packages/denckring-fr-data/src/denckring_fr_data/data/*.txt.gz` | `words`, `nouns`, `graded_words`, `glosses` |
| `packages/denckring-fr-data/src/denckring_fr_data/data/metadata.json` | Counts and generation date |
| `tests/test_lang_fr_data.py` | The pack's invariants |
| `src/denckring/data/catalogue.yaml` | `languages` gains `fr` on 11 rows; 3 rows gain French names and definitions |
| `src/denckring/eval/fixtures/golden/*.yaml` | French cases for those 11 rows |
| `docs/adr/0032-the-french-lexicon.md` | The source decision |

---

### Task 1: The distribution skeleton

**Files:**
- Create: `packages/denckring-fr-data/pyproject.toml`, `LICENSE`, `LICENSE-LEXIQUE`, `LICENSE-WIKTIONARY`, `NOTICE`, `README.md`
- Create: `packages/denckring-fr-data/src/denckring_fr_data/__init__.py`, `py.typed`
- Modify: `pyproject.toml` (root) — `[project.optional-dependencies]` and `[tool.uv.sources]`
- Test: `tests/test_lang_fr_data.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `denckring_fr_data` module; the `fr` extra; `denckring_fr_data.__version__`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lang_fr_data.py`:

```python
"""The French lexicon's own invariants.

Skipped in full when `denckring[fr]` is not installed, exactly as the German and
English data tests skip without theirs.
"""

import pytest

fr_data = pytest.importorskip("denckring_fr_data", reason="needs denckring[fr]")


def test_the_distribution_is_importable_and_versioned() -> None:
    assert fr_data.__version__ == "0.1.0"
```

- [ ] **Step 2: Run it and watch it skip**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: SKIPPED, "needs denckring[fr]" — the package does not exist yet.

- [ ] **Step 3: Create the package**

`packages/denckring-fr-data/pyproject.toml`:

```toml
[project]
name = "denckring-fr-data"
version = "0.1.0"
description = "French lexicon data for denckring: word membership, nouns, frequency bands and glosses"
readme = "README.md"
requires-python = ">=3.11"
license = "Apache-2.0 AND CC-BY-SA-4.0"
license-files = ["LICENSE", "NOTICE", "LICENSE-LEXIQUE", "LICENSE-WIKTIONARY"]
authors = [{ name = "senzelden", email = "senzelden@gmail.com" }]
classifiers = [
    "Intended Audience :: Science/Research",
    "Natural Language :: French",
    "Topic :: Text Processing :: Linguistic",
    "Typing :: Typed",
]
# Version-locked, for the reason denckring-en-data records.
dependencies = ["denckring==0.1.0"]

# A class, not a factory. German needs `denckring_de_data:pack` because its data
# is split across a CC0 distribution and a CC BY-SA one and only one may claim
# `fr`'s equivalent (ADR 0030). French has one distribution and both its sources
# carry the same licence, so there is nothing to choose between.
[project.entry-points."denckring.lang"]
fr = "denckring_fr_data:FrenchDataPack"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/denckring_fr_data"]
```

`packages/denckring-fr-data/src/denckring_fr_data/__init__.py`:

```python
"""French lexicon data for denckring.

Installing this gives the French pack `lexicon.words`, `lexicon.nouns`,
`lexicon.glosses` and `lexicon.graded_words`. Nothing branches on whether it is
present — the same procedures answer the same calls, in a third language.

Two sources, both CC BY-SA 4.0: Lexique 3.82 for membership, nouns and frequency,
and French Wiktionary for definitions. ADR 0032 records why Wikidata Lexemes,
which supplies German, could not supply French.
"""

from __future__ import annotations

__version__ = "0.1.0"
```

Create an empty `packages/denckring-fr-data/src/denckring_fr_data/py.typed`.

Copy the Apache licence: `cp packages/denckring-de-data/LICENSE packages/denckring-fr-data/LICENSE`.

`packages/denckring-fr-data/NOTICE`:

```
denckring-fr-data
Copyright 2026 senzelden

The code in this distribution is licensed under the Apache License, Version 2.0.
See LICENSE.

The data in this distribution comes from two sources, both licensed under the
Creative Commons Attribution-ShareAlike 4.0 International licence:

  - Lexique 3.82 (lexique.org) — see LICENSE-LEXIQUE
  - French Wiktionary — see LICENSE-WIKTIONARY

Both impose attribution and share-alike. That they agree is why this is one
distribution where German needs two: ADR 0013 quarantines a data licence per
distribution, and there is only one licence here to quarantine.
```

`packages/denckring-fr-data/LICENSE-LEXIQUE`:

```
The French word list, noun list and frequency bands in this distribution are
derived from Lexique 3.82.

    New, B., Pallier, C., Ferrand, L., Matos, R. (2001). Une base de données
    lexicales du français contemporain sur internet: LEXIQUE. L'Année
    Psychologique, 101, 447-462.
    http://www.lexique.org

Lexique is licensed under the Creative Commons Attribution-ShareAlike 4.0
International licence, as stated in the README bundled with Lexique382.zip:

    https://creativecommons.org/licenses/by-sa/4.0/

Attribution: Boris New and Christophe Pallier, and the Lexique contributors.

Share-alike: the derived data files in this distribution
(`src/denckring_fr_data/data/`) are offered under the same CC BY-SA 4.0 licence.
The code in this distribution is Apache-2.0 and is not a derivative of the data.

Regenerate the vendored files with scripts/build_lexicon.py.
```

`packages/denckring-fr-data/LICENSE-WIKTIONARY`:

```
The French glosses in this distribution are derived from French Wiktionary
(https://fr.wiktionary.org), specifically from the
`frwiktionary-latest-pages-articles` XML dump published by the Wikimedia
Foundation.

Wiktionary text is licensed under the Creative Commons
Attribution-ShareAlike 4.0 International licence:

    https://creativecommons.org/licenses/by-sa/4.0/

Attribution: the French Wiktionary contributors. Page histories, which name
them, are at https://fr.wiktionary.org/wiki/<headword> under "Historique".

Share-alike: the derived data files in this distribution are offered under the
same CC BY-SA 4.0 licence.

Regenerate the vendored files with scripts/build_lexicon.py.
```

`packages/denckring-fr-data/README.md`:

```markdown
# denckring-fr-data

French lexicon data for [denckring](https://github.com/senzelden/denckring):
word membership, an ordered noun list, frequency bands and glosses.

```console
pip install denckring[fr]
```

Installing this gives the French pack `lexicon.words`, `lexicon.nouns`,
`lexicon.glosses` and `lexicon.graded_words`, which is what `charade`,
`semordnilap`, `word_square`, `n_plus_7`, `s_plus_7`, `tmesis`, `word_ladder`,
`kangaroo_word` and the two definitional rows need in order to run in French —
and what `apply anagram` needs in order to generate in it. Without it those
procedures raise `MissingCapability` for `fr`, exactly as for any unmet
capability.

The data is **CC BY-SA 4.0** — attribution *and* share-alike — from Lexique 3.82
and French Wiktionary. See `LICENSE-LEXIQUE` and `LICENSE-WIKTIONARY`.
Regenerate the vendored files with `scripts/build_lexicon.py`.

Accents are preserved rather than folded. `côte` and `cote` are different words,
and whether they should be treated alike is a decision ADR 0009 leaves to the
procedure, not to the lexicon.

This distribution supplies no prosody. French has no lexical stress, and the
syllable capabilities wait on the line-level counter that chapter 6 tranche B
designs; see ADR 0032 and the chapter spec.
```

Register it in the root `pyproject.toml`. Under `[project.optional-dependencies]`, after the `de-wiktionary` line:

```toml
# Word membership, an ordered noun list, frequency bands and glosses for French,
# from Lexique 3.82 and French Wiktionary. Both CC BY-SA, so one distribution.
fr = ["denckring-fr-data==0.1.0"]
```

Under `[tool.uv.sources]`, after `denckring-de-wiktionary`:

```toml
denckring-fr-data = { workspace = true }
```

- [ ] **Step 4: Sync and run the test**

Run: `uv sync --all-extras && uv run pytest tests/test_lang_fr_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/denckring-fr-data pyproject.toml uv.lock tests/test_lang_fr_data.py
git commit -m "feat: denckring-fr-data, the fifth distribution

Skeleton only: metadata, licences and an entry point. Both its sources are
CC BY-SA, so unlike German it is one distribution and the entry point resolves
to a class rather than to a factory.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 2: Build the word, noun and frequency tables from Lexique

**Files:**
- Create: `packages/denckring-fr-data/scripts/build_lexicon.py`
- Create (generated): `.../data/words.txt.gz`, `nouns.txt.gz`, `graded_words.txt.gz`, `metadata.json`
- Test: `tests/test_lang_fr_data.py`

**Interfaces:**
- Consumes: Task 1's package.
- Produces: three gzipped tables. `words.txt.gz` is one form per line. `nouns.txt.gz` is one noun per line in dictionary order. `graded_words.txt.gz` is `word\tband` where **band is 10, 20, 30, 40, 50 or 60 and larger means less common**.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lang_fr_data.py`:

```python
def test_the_bands_run_the_project_s_way_and_not_the_source_s() -> None:
    """Lexique's frequencies rise with commonness; `graded_words` bands fall with
    it, matching SCOWL and what `anagram` sorts by. The build inverts, and a
    source's convention leaking through here would silently rank every French
    anagram backwards. ADR 0032."""
    bands = fr_data.graded_words()
    assert bands["être"] < bands["nonobstant"]
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
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: FAIL, `AttributeError: module 'denckring_fr_data' has no attribute 'graded_words'`.

- [ ] **Step 3: Write the build script**

Create `packages/denckring-fr-data/scripts/build_lexicon.py`:

```python
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
    counts = {**existing.get("counts", {}), WORDS.name: len(words), NOUNS.name: len(nouns),
              GRADED.name: len(bands)}
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
```

- [ ] **Step 4: Add the readers**

Append to `packages/denckring-fr-data/src/denckring_fr_data/__init__.py`:

```python
import gzip
from collections.abc import Mapping
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "words.txt.gz"))
NOUNS_PATH = Path(str(files("denckring_fr_data") / "data" / "nouns.txt.gz"))
GRADED_WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "graded_words.txt.gz"))


def _read(path: Path) -> tuple[str, ...]:
    """Every line of a gzipped list.

    A truncated file raises rather than returning a short list: a short noun list
    makes N+7 quietly wrong, and a wrong answer is worse than an exception.
    """
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return tuple(line for line in handle.read().split("\n") if line)


@lru_cache(maxsize=1)
def noun_list() -> tuple[str, ...]:
    """Every noun form, in dictionary order. N+7 walks this, so order is the point."""
    return _read(NOUNS_PATH)


@lru_cache(maxsize=1)
def noun_positions() -> dict[str, int]:
    return {word.casefold(): index for index, word in enumerate(noun_list())}


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """Membership, from every form Lexique carries."""
    return frozenset(_read(WORDS_PATH))


@lru_cache(maxsize=1)
def graded_words() -> Mapping[str, int]:
    """Word to band, where **larger means less common** — SCOWL's direction."""
    table: dict[str, int] = {}
    with gzip.open(GRADED_WORDS_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            word, _, band = line.rstrip("\n").partition("\t")
            if band:
                table[word] = int(band)
    return table
```

- [ ] **Step 5: Run the build**

```bash
cd packages/denckring-fr-data
uv run --project ../.. python scripts/build_lexicon.py --lexique /path/to/Lexique382.zip
```

Expected: prints a line like `125653 words, 48234 nouns, 125653 bands`.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: PASS, all four.

- [ ] **Step 7: Commit**

```bash
git add packages/denckring-fr-data tests/test_lang_fr_data.py
git commit -m "feat: French words, nouns and frequency bands from Lexique 3.82

Bands are inverted against the source: Lexique's frequencies rise with
commonness and \`graded_words\` falls with it, which is SCOWL's direction and
what \`anagram\` sorts by. A test pins the direction, because a source's
convention leaking into a capability's contract would rank every French anagram
backwards and nothing else would notice.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 3: Build the glosses from the Wiktionary dump

**Files:**
- Modify: `packages/denckring-fr-data/scripts/build_lexicon.py`
- Create (generated): `.../data/glosses.txt.gz`
- Test: `tests/test_lang_fr_data.py`

**Interfaces:**
- Consumes: Task 2's script and `metadata.json`.
- Produces: `glosses.txt.gz`, one `headword\tsense | sense | sense` line per entry, and `denckring_fr_data.gloss_table() -> dict[str, tuple[str, ...]]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lang_fr_data.py`:

```python
def test_glosses_carry_every_sense_in_wiktionary_s_order() -> None:
    """Every sense, not the first: which sense a writer meant is not knowable from
    the text, so a caller that accepts any of them is the honest reader."""
    senses = fr_data.gloss_table()["maison"]
    assert len(senses) > 3
    assert "bâtiment" in senses[0].casefold()


def test_a_headword_with_no_definition_is_absent_rather_than_empty() -> None:
    assert "zzzzqq" not in fr_data.gloss_table()
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: FAIL, `AttributeError: module 'denckring_fr_data' has no attribute 'gloss_table'`.

- [ ] **Step 3: Add the extraction to the build script**

Add to `packages/denckring-fr-data/scripts/build_lexicon.py`, after the imports:

```python
import bz2
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator

DUMP_URL = (
    "https://dumps.wikimedia.org/frwiktionary/latest/frwiktionary-latest-pages-articles.xml.bz2"
)
GLOSSES = DATA / "glosses.txt.gz"

#: The dump's export schema version appears in every tag name. Read from the root
#: element rather than hardcoded, because Wikimedia bumps it.
_NS = re.compile(r"^\{([^}]+)\}")
#: A language section runs from its own heading to the next one.
_FRENCH = re.compile(r"^==\s*\{\{langue\|fr\}\}\s*==\s*$", re.M)
_ANY_LANGUAGE = re.compile(r"^==\s*\{\{langue\|[^}]+\}\}\s*==\s*$", re.M)
#: A sense is a `#` line. `#*` is an example sentence under one, and `#:` a
#: usage note; neither is a definition, hence the negative lookahead.
_SENSE = re.compile(r"^#\s+(?!\*)(.+)$", re.M)


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
            senses = [s for s in (_strip_markup(m) for m in _SENSE.findall(section)) if s]
            # `" | "` is the separator downstream, so a sense containing it is
            # dropped rather than escaped: splitting must be unambiguous, and
            # `denckring-en-data` and `denckring-de-wiktionary` both split this way.
            usable = [s for s in dict.fromkeys(senses) if " | " not in s and "\t" not in s]
            if usable:
                yield title, usable
```

In `main`, add a `--dump` argument and the write:

```python
    parser.add_argument("--dump", type=Path, help="A downloaded frwiktionary dump.")
```

and after the three Lexique tables are written:

```python
    if args.dump is not None:
        rendered = [(title, " | ".join(senses)) for title, senses in glosses_from(args.dump)]
        payload = "".join(f"{k}\t{v}\n" for k, v in rendered).encode("utf-8")
        with gzip.GzipFile(GLOSSES, "wb", mtime=0) as handle:
            handle.write(payload)
        counts[GLOSSES.name] = len(rendered)
        print(f"{len(rendered)} glosses", file=sys.stderr)
```

- [ ] **Step 4: Add the reader**

Append to `packages/denckring-fr-data/src/denckring_fr_data/__init__.py`:

```python
GLOSSES_PATH = Path(str(files("denckring_fr_data") / "data" / "glosses.txt.gz"))


@lru_cache(maxsize=1)
def gloss_table() -> dict[str, tuple[str, ...]]:
    """Headword to every sense's definition, in Wiktionary's order.

    Split on `" | "` rather than `"|"`, because a definition may contain a bare
    pipe and the build rejects any that contains the spaced separator.
    """
    with gzip.open(GLOSSES_PATH, mode="rt", encoding="utf-8") as handle:
        return {
            key: tuple(values.split(" | "))
            for key, _, values in (line.rstrip("\n").partition("\t") for line in handle)
            if values
        }
```

- [ ] **Step 5: Run the build with the dump**

```bash
cd packages/denckring-fr-data
uv run --project ../.. python scripts/build_lexicon.py \
  --lexique /path/to/Lexique382.zip --dump /path/to/frwiktionary-latest-pages-articles.xml.bz2
```

Expected: prints the three Lexique counts and then a glosses count.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/denckring-fr-data tests/test_lang_fr_data.py
git commit -m "feat: French glosses from the Wiktionary dump

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 4: `FrenchDataPack`

**Files:**
- Modify: `packages/denckring-fr-data/src/denckring_fr_data/__init__.py`
- Test: `tests/test_lang_fr_data.py`

**Interfaces:**
- Consumes: Tasks 2 and 3's readers.
- Produces: `FrenchDataPack`, declaring `TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, NOUNS, WORDS, GLOSSES, GRADED_WORDS`, with `is_word`, `nouns`, `noun_index`, `glosses`, `graded_words`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lang_fr_data.py`:

```python
from denckring.core.errors import MissingCapability
from denckring.lang.base import GLOSSES, GRADED_WORDS, NOUNS, PHONEMES, STRESS, WORDS


def test_the_pack_declares_the_four_lexical_capabilities_and_no_prosody() -> None:
    pack = fr_data.FrenchDataPack()
    for capability in (WORDS, NOUNS, GLOSSES, GRADED_WORDS):
        assert capability in pack.capabilities
    # French has no lexical stress and this tranche ships no syllable data.
    # Declaring either would be the false-capability defect ADR 0030 fixed twice.
    for capability in (PHONEMES, STRESS):
        assert capability not in pack.capabilities
    with pytest.raises(MissingCapability):
        pack.phonemes("maison")


def test_accents_are_kept_because_cote_and_cote_are_different_words() -> None:
    pack = fr_data.FrenchDataPack()
    assert pack.is_word("côte")
    assert pack.noun_index("côte") != pack.noun_index("cote")


def test_the_entry_point_gives_this_pack() -> None:
    from denckring.lang import get_pack

    assert isinstance(get_pack("fr"), fr_data.FrenchDataPack)
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: FAIL, `AttributeError: module 'denckring_fr_data' has no attribute 'FrenchDataPack'`.

- [ ] **Step 3: Write the pack**

Append to `packages/denckring-fr-data/src/denckring_fr_data/__init__.py`:

```python
from types import MappingProxyType
from typing import ClassVar

from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    GLOSSES,
    GRADED_WORDS,
    LETTER_SHAPES,
    NOUNS,
    TOKENS,
    WORDS,
)
from denckring.lang.fr import FrenchPack


class FrenchDataPack(FrenchPack):
    """French with a lexicon behind it.

    A fixed `ClassVar`, as on every pack but German's: this distribution has one
    licence and one set of data, so there is nothing for the install to change.
    """

    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, NOUNS, WORDS, GLOSSES, GRADED_WORDS}
    )

    def is_word(self, word: str) -> bool:
        return self._lemma(word) in known_words()

    def nouns(self) -> tuple[str, ...]:
        return noun_list()

    def noun_index(self, word: str) -> int | None:
        return noun_positions().get(self._lemma(word))

    def glosses(self, word: str) -> tuple[str, ...]:
        """Every sense, or nothing. Empty rather than raising, matching English."""
        return gloss_table().get(self._lemma(word), ())

    def graded_words(self) -> Mapping[str, int]:
        """A read-only view over the cached table, for the reason English gives:
        the module function is `lru_cache`d and shared, so handing the dict out
        would let one caller's mutation corrupt it for all the others."""
        return MappingProxyType(graded_words())

    @staticmethod
    def _lemma(word: str) -> str:
        """Casefold, and keep accents.

        English strips to ASCII here. French must not: `fold_diacritics` would
        collide `côte` with `cote` and `pêcheur` with `pecheur`, and ADR 0009
        makes folding a parameter of the procedure rather than a property of the
        lexicon. German keeps its umlauts for the same reason.
        """
        return "".join(ch for ch in word.casefold() if ch.isalpha())
```

- [ ] **Step 4: Run the tests**

Run: `uv sync --all-extras && uv run pytest tests/test_lang_fr_data.py -v`
Expected: PASS.

- [ ] **Step 5: Check the coverage moved**

```bash
uv run python -c "
from denckring.core.registry import all_procedures
from denckring.lang import get_pack
caps = set(get_pack('fr').capabilities)
runs = [p for p in all_procedures().values() if set(p.meta.requires) <= caps]
print('fr', len(runs), 'of', len(all_procedures()))
"
```

Expected: `fr 80 of 121`.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-fr-data tests/test_lang_fr_data.py uv.lock
git commit -m "feat: FrenchDataPack, taking French from 70 to 80 of 121

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 5: The catalogue tells the truth about French

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`
- Test: existing `tests/test_catalogue_quality.py`, `tests/test_invariants.py`

**Interfaces:**
- Consumes: Task 4's pack.
- Produces: eleven rows declaring `fr`. This task fails its own tests until Task 6 supplies the golden cases — see Step 4.

- [ ] **Step 1: Write French names and definitions for the three rows that lack them**

`definitional_expansion`, `kangaroo_word` and `semordnilap` carry no `names.fr` or
`definitions.fr`. Add them, matching the register of the existing French text:

```yaml
# definitional_expansion
      fr: Expansion définitionnelle
# and under definitions:
      fr: >-
        Chaque mot substantiel est remplacé par une de ses définitions de
        dictionnaire, le texte enflant d'un tour à l'autre.
```

```yaml
# kangaroo_word
      fr: Mot kangourou
      fr: >-
        Un mot qui contient son propre synonyme, dans l'ordre, lettres non
        contiguës admises.
```

```yaml
# semordnilap
      fr: Sémordnilap
      fr: >-
        Un mot qui, lu à l'envers, donne un autre mot — à la différence du
        palindrome, qui redonne le même.
```

- [ ] **Step 2: Add `fr` to `languages` on eleven rows**

`charade`, `definitional_expansion`, `definitional_literature`, `kangaroo_word`,
`n_plus_7`, `s_plus_7`, `semordnilap`, `tmesis`, `word_ladder`, `word_square`, `anagram`.

`anagram` is in the list because its checker already ran in French; what this tranche adds
is `lexicon.graded_words`, so `apply anagram` now generates in French too.

- [ ] **Step 3: Run the catalogue tests**

Run: `uv run pytest tests/test_catalogue_quality.py tests/test_invariants.py -q`
Expected: FAIL on `test_every_declared_language_has_a_golden_case` for all eleven — a
declared language must have a golden case, and Task 6 writes them. This failure is the
point: it is the project's bar for a row gaining a language, and it is what stops a row
claiming French on the strength of a capability check alone.

- [ ] **Step 4: Do not commit yet**

This task's deliverable is not independently green. Carry it into Task 6 and commit them
together.

---

### Task 6: French golden cases

**Files:**
- Modify: eleven files under `src/denckring/eval/fixtures/golden/`
- Test: `uv run denckring eval --all`

**Interfaces:**
- Consumes: Tasks 4 and 5.
- Produces: at least one French case per declared row.

- [ ] **Step 1: Verify every candidate case against its own checker before writing it down**

Do not hand-write fixtures and hope. Build them the way chapter 4 built the German ones:
write candidates in a scratch script, run each through `check`, and only transcribe the
ones whose verdict matches the claim.

```python
from denckring import check

CASES = [
    ("semordnilap", "suc cus", {}, True),
    ("charade", "portemanteau", {}, True),
    ("word_square", "roc\nova\ncas", {}, True),
    ("n_plus_7", "...", {"source": "..."}, True),
]
for pid, text, params, want in CASES:
    report = check(pid, text, lang="fr", **params)
    print("OK " if report.satisfied == want else "BAD", pid, report.score,
          [v.rule for v in report.violations[:3]])
```

Iterate until every line prints `OK`. The `...` placeholders above are deliberate: the
actual French text is what this step produces, and inventing it here without running it
is exactly the failure this step exists to prevent.

- [ ] **Step 2: Write the verified cases into the fixtures**

Append to each row's YAML, in the established shape:

```yaml
  - name: <kebab-case-french-name>
    lang: fr
    source: constructed example
    text: |-
      <the verified text>
    params: {}
    satisfied: true
```

Every row needs at least one case. Prefer a positive and a negative where the negative is
cheap, which is the project's normal bar.

- [ ] **Step 3: Run the eval and the suite**

Run: `uv run denckring eval --all && uv run pytest -q`
Expected: `121 procedures · <more than 417> passed · 0 failed`, and a green suite.

- [ ] **Step 4: Run the whole gate**

```bash
uv run pytest -q
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src \
  packages/denckring-de-wiktionary/src packages/denckring-fr-data/src
uv run ruff check .
uv run ruff format --check .
uv run denckring status
```

Expected: all green. `status` is unchanged — it counts implemented rows, and these were
always implemented.

- [ ] **Step 5: Commit Tasks 5 and 6 together**

```bash
git add src/denckring/data/catalogue.yaml src/denckring/eval/fixtures/golden
git commit -m "feat: eleven rows declare French, with golden cases to back it

Not one of the 155 catalogue rows declared \`fr\` before this, while 49 are
sourced to French authors or the Oulipo -- \`lipogram\` to Perec's La
Disparition, \`cent_mille_milliards\` to Queneau. The catalogue was silent about
French even where French is the source language.

Three rows needed French names and definitions written before they could
declare it.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 7: ADR 0032, CI, and the changelog

**Files:**
- Create: `docs/adr/0032-the-french-lexicon.md`
- Modify: `mkdocs.yml`, `.github/workflows/ci.yml`, `CHANGELOG.md`, `README.md`
- Test: `tests/test_readme.py`

**Interfaces:**
- Consumes: everything above.
- Produces: the decision record and a CI job proving the without-data path.

- [ ] **Step 1: Write ADR 0032**

State the problem (French at 70 of 121, ADR 0023's source measured and rejected), the
decision (Lexique + Wiktionary, one distribution, a class not a factory, bands inverted),
and consequences that admit costs. Required numbers, all measured on 2026-08-31:

- Wikidata Lexemes: 31,474 French lexemes, 12,768 noun lexemes, against German's 241,979
  and 188,948 — 6.8% of German's nouns
- Lexique 3.82: 142,694 rows, 125,653 distinct forms, 46,947 lemmas, 48,234 noun forms,
  CC BY-SA 4.0
- The costs to admit: a five-way version lockstep; every French capability inherits
  share-alike with no CC0 tier possible; the band bucketing is arbitrary; French declares
  no prosody and 41 rows stay blocked, 18 of them permanently (D2 of the spec).

- [ ] **Step 2: Add it to the docs nav**

In `mkdocs.yml`, after the ADR 0031 line:

```yaml
      - "32. The French lexicon": adr/0032-the-french-lexicon.md
```

- [ ] **Step 3: Add the extra to every CI job that syncs, and add the without-data job**

In `.github/workflows/ci.yml`, change every `uv sync --extra en --extra de --extra
de-wiktionary` to add `--extra fr`. Then add, after `german-without-pronunciations`:

```yaml
  french-without-data:
    # French ships in core with no data at all, which is a real install shape and
    # the one the suite never runs. A syllabic or lexical row must refuse by
    # naming what is missing rather than guessing.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install the core distribution alone
        run: |
          uv venv /tmp/fr-core
          VIRTUAL_ENV=/tmp/fr-core uv pip install .
      - name: The data-free French rows work and the lexical ones name what is missing
        run: |
          /tmp/fr-core/bin/python -c "
          from denckring import check
          from denckring.core.errors import MissingCapability
          assert check('lipogram', 'aaa', forbidden='z', lang='fr').satisfied
          try:
              check('n_plus_7', 'la maison', lang='fr')
          except MissingCapability as exc:
              assert 'lexicon.nouns' in str(exc), exc
              print('fr-core: raised as expected —', exc)
          else:
              raise SystemExit('n_plus_7 needs lexicon.nouns, which this install lacks')
          "
```

- [ ] **Step 4: Update the README**

Add to the install block:

```console
pip install denckring[fr]      # + a word list, nouns, frequency bands and glosses
```

and update the French paragraph, which currently reads "there is no `[fr]` extra to
install" and "70 of the 121 implemented rows run in it" — both now false.

- [ ] **Step 5: Write the changelog entry, then run the whole gate**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: green, including `tests/test_readme.py`, which checks the README's counts
against what the harness reports.

- [ ] **Step 6: Commit**

```bash
git add docs/adr mkdocs.yml .github/workflows/ci.yml CHANGELOG.md README.md
git commit -m "docs: ADR 0032, the French lexicon

Assisted-by: Claude:claude-opus-5[1m]"
```

---

## Tranche B is gated, and the gate is a measurement

**Do not start tranche B from this plan.** Its first action is a throwaway prototype, not
a component: implement the mute-e elision rules against Lexique's syllable counts, run
them over Racine and Hugo alexandrines, and report the share of lines scored at exactly
twelve.

That figure is D3's go/no-go and it can fail. If it is poor, the line-level seam is the
wrong design and the chapter stops at 80 rather than shipping a counter that is confidently
wrong about French verse — which is the defect class ADR 0030 fixed twice in one day. The
prototype is labelled throwaway and none of it is kept.

Tranche B gets its own plan, written after that measurement, exactly as chapter 4's
tranche B was planned only after the dewiktionary dump was measured.

## Self-review

**Spec coverage.** F1 → Task 1. F2 → Task 4. F5 → Task 6. The build script covering both
sources → Tasks 2 and 3. D1 (one distribution, class not factory) → Task 1's pyproject
comment and Task 4's docstring. D6 (band inversion) → Task 2, with a test. D2 (no stress)
→ Task 4's capability test. **F0, F3 and F4 are tranche B and are correctly absent** —
F0's SAMPA table, F3's line seam and F4's aspirated-*h* list all belong to prosody.

**Gap found and left open deliberately:** the spec's Testing section asks for a Lexique
coverage measurement over French text. Tranche A's rows do not depend on it — membership
and nouns are answered by presence, not by coverage — and the measurement that matters is
tranche B's alexandrine figure. Task 7's ADR carries the source counts instead.

**Type consistency.** `known_words() -> frozenset[str]`, `noun_list() -> tuple[str, ...]`,
`noun_positions() -> dict[str, int]`, `graded_words() -> Mapping[str, int]`,
`gloss_table() -> dict[str, tuple[str, ...]]` — used consistently in Tasks 2, 3 and 4.
`FrenchDataPack.glosses` returns `tuple[str, ...]`, widening the protocol's
`Sequence[str]`, which is what `EnglishDataPack.glosses` does.

**Placeholder scan.** One deliberate `...`, in Task 6 Step 1, where the placeholder *is*
the instruction: the French text is the output of running the checker, and writing it into
the plan unverified is the failure that step exists to prevent.
