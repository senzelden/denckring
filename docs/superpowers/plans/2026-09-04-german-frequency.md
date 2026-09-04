# German frequency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the German pack `lexicon.graded_words` from the Leipzig Corpora Collection, so `anagram` can generate in German as it already does in English and French.

**Architecture:** A sixth workspace distribution, `denckring-de-frequency`, carrying one gzipped `word ⇥ band` table built from a Leipzig news corpus. It registers no entry point; `denckring_de_data:pack()` composes it in, the way it already composes `denckring-de-wiktionary`. The build's one non-obvious rule is that a German noun is counted only from capitalised corpus rows.

**Tech Stack:** Python 3.11, hatchling, pydantic v2, pytest, mypy --strict, ruff.

**Spec:** `docs/superpowers/specs/2026-09-04-german-frequency-design.md`

## Global Constraints

- **The gate is four commands**, then two more for anything touching a procedure: `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`, `uv run ruff format --check .`, then `uv run denckring eval --all` and `uv run denckring status`.
- **CI type-checks the workspace packages and the four-command gate does not.** Anything touching a data distribution must run the longer form, which this plan extends: `uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src packages/denckring-de-wiktionary/src packages/denckring-de-frequency/src`.
- **Expected counters, unchanged by this plan**: `denckring status` reads `156 · 131 · 122 · 122 · 25`, then `0 instruments catalogued`. `eval --all` reads `122 procedures · 528 passed · 0 failed` plus whatever Task 7 adds.
- **`apps/explorer` has its own gate**, run from inside the app: `cd apps/explorer && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests && uv run pytest`. Expect `367 passed` before Task 8.
- **Commit trailer is `Assisted-by: Claude:claude-opus-5[1m]`.** Never `Co-Authored-By:`, never `Signed-off-by:`, never `Claude-Session:`.
- **Stage files by name.** Never `git add -A`.
- **Do not push.** `origin/main` is pinned at `f0ffdcb` by decision until release.
- **`procedure_id` is a reserved test-argument name** — `tests/conftest.py` auto-parametrises it. Name the argument `pid`.
- **Comments explain why, not what, and cite ADRs by number.** A comment that has become false is a defect here.
- **The licence version is a blocker for Task 1 alone.** The Leipzig terms say "the Creative Commons licence CC BY" with no version; the archive carries no licence file and `meta.txt` names none. Do not write `CC-BY-4.0` into a `license` field on the strength of a search result — an SPDX identifier is a claim. Task 1 stops until the version is established from the project's own page or by asking them, which their terms invite.
- **Never re-download the corpus in a test.** It is 219 MB. Tests use fixtures shaped like Leipzig rows.

---

### Task 1: The distribution skeleton

**Files:**
- Create: `packages/denckring-de-frequency/pyproject.toml`
- Create: `packages/denckring-de-frequency/README.md`
- Create: `packages/denckring-de-frequency/LICENSE`, `NOTICE`, `LICENSE-LEIPZIG`
- Create: `packages/denckring-de-frequency/src/denckring_de_frequency/__init__.py`
- Create: `packages/denckring-de-frequency/src/denckring_de_frequency/py.typed`
- Modify: `pyproject.toml` (root — the `de-frequency` extra and the workspace source)

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `denckring_de_frequency` package. Task 3 adds `graded_words()` and `GRADED_WORDS_PATH` to it; Task 4 adds the pack classes.

- [ ] **Step 1: Establish the CC BY version before anything else**

Open the Leipzig download page in a browser and read the terms beside the download links, or write to the project as their terms invite. Record the exact version. **Do not proceed to Step 2 without it** — every file below carries the licence expression, and a wrong SPDX identifier is a false claim in package metadata that propagates to PyPI.

If the answer is 4.0 the expression is `Apache-2.0 AND CC-BY-4.0`; if 3.0, `Apache-2.0 AND CC-BY-3.0`. Substitute below.

- [ ] **Step 2: Write the pyproject, modelled on `denckring-de-data`**

```toml
[project]
name = "denckring-de-frequency"
version = "0.1.0"
description = "German frequency bands for denckring, from the Leipzig Corpora Collection"
readme = "README.md"
requires-python = ">=3.11"
license = "Apache-2.0 AND CC-BY-4.0"
license-files = ["LICENSE", "NOTICE", "LICENSE-LEIPZIG"]
authors = [{ name = "senzelden", email = "senzelden@gmail.com" }]
classifiers = [
    "Intended Audience :: Science/Research",
    "Natural Language :: German",
    "Topic :: Text Processing :: Linguistic",
    "Typing :: Typed",
]
# Version-locked, for the reason denckring-en-data records.
dependencies = ["denckring-de-data==0.1.0"]

# No [project.entry-points."denckring.lang"] section, and its absence is the
# design — the same absence denckring-de-wiktionary documents.
# `denckring/lang/__init__.py` refuses two entry points claiming one language,
# so `de` stays with denckring-de-data and its `pack()` factory composes this
# distribution in when it is importable (ADR 0013, ADR 0030).

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/denckring_de_frequency"]
```

`dependencies` names `denckring-de-data`, not `denckring`, for a real reason: Task 3's build rule needs `nouns()` to know which forms are German nouns, and Task 4's pack subclasses `GermanDataPack`. The dependency runs the same direction `denckring-de-wiktionary`'s does.

- [ ] **Step 3: Write `LICENSE-LEIPZIG`**

Attribution is the whole of CC BY's requirement, so name the source exactly:

```
The frequency data in this distribution is derived from the Leipzig Corpora
Collection (corpus deu_news_2023_1M), © Universität Leipzig / Sächsische
Akademie der Wissenschaften / InfAI, made available under the Creative Commons
Attribution licence.

    https://corpora.uni-leipzig.de/

Only a derived table is redistributed here: each word is paired with a band
from 10 to 60 giving its frequency rank, and no sentence, co-occurrence or
source list from the corpus is included.

D. Goldhahn, T. Eckart, U. Quasthoff. Building Large Monolingual Dictionaries
at the Leipzig Corpora Collection: From 100 to 200 Languages. LREC 2012.
```

Copy `LICENSE` and `NOTICE` from `packages/denckring-de-data/`, changing only what names the data source.

- [ ] **Step 4: Write the package `__init__.py` stub with the path constant**

```python
"""German frequency bands, from the Leipzig Corpora Collection.

The sixth distribution, and the third carrying German data under a third
licence: `denckring-de-data` is CC0 Wikidata, `denckring-de-wiktionary` is
CC BY-SA, and this is CC BY. ADR 0013 quarantines a data licence in its own
distribution, and CC BY cannot join the CC0 package — CC0 waives rights where
CC BY requires attribution, so adding it would make that declaration false.

Registers no entry point. See the pyproject for why.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

GRADED_WORDS_PATH = Path(str(files("denckring_de_frequency") / "data" / "graded_words.txt.gz"))

__all__ = ["GRADED_WORDS_PATH"]
```

Create an empty `py.typed`, and `src/denckring_de_frequency/data/.gitkeep` so the directory exists before Task 3 fills it.

- [ ] **Step 5: Register it in the workspace**

In the **root** `pyproject.toml`, add the extra beside the others:

```toml
# Frequency bands for German, from the Leipzig Corpora Collection. A separate
# extra because its data is CC BY where `de`'s is CC0, and ADR 0013 quarantines
# a data licence in its own distribution. Light — 434 KB — and deliberately
# independent of `de-wiktionary`, so German `anagram` does not drag in 6.5 MB of
# pronunciations it never reads.
de-frequency = ["denckring-de-data==0.1.0", "denckring-de-frequency==0.1.0"]
```

and add `denckring-de-frequency = { workspace = true }` to `[tool.uv.sources]`. `[tool.uv.workspace] members = ["packages/*"]` already covers the new directory.

- [ ] **Step 6: Verify it builds and imports**

Run: `uv sync && uv run python -c "import denckring_de_frequency as f; print(f.GRADED_WORDS_PATH)"`
Expected: a path ending `data/graded_words.txt.gz`. The file does not exist yet; that is Task 3.

- [ ] **Step 7: Commit**

```bash
git add packages/denckring-de-frequency pyproject.toml uv.lock
git commit -m "feat: denckring-de-frequency, a sixth distribution

German frequency data is CC BY, which cannot enter the CC0 package: CC0
waives rights where CC BY requires attribution. ADR 0013 quarantines a data
licence in its own distribution, and this is German's third.

No entry point, the same absence denckring-de-wiktionary documents.
Deliberately independent of de-wiktionary, so German anagram does not pull
in 6.5 MB of pronunciations it never reads.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 2: The case rule, tested before any corpus is downloaded

**Files:**
- Create: `packages/denckring-de-frequency/scripts/build_frequency.py`
- Create: `tests/test_de_frequency_build.py`

**Interfaces:**
- Consumes: `denckring_de_data`'s `known_words()`, and `GermanDataPack().nouns()`.
- Produces: `bands(rows: list[tuple[str, int]], known: set[str], nouns_lower: set[str]) -> dict[str, int]`, importable by the test. `rows` are `(form, count)` pairs with the corpus's own case.

This task is first among the build work because the case rule is the decision the whole chapter turns on, and it is the one that has already been got wrong twice — once by using a source that destroyed case, once by lowercasing before intersecting.

- [ ] **Step 1: Write the failing test**

```python
"""The case rule — ADR 0038 D3, and the thing this chapter turns on.

German capitalises common nouns. A source that keeps case therefore tells
German `Tag` from English `tag`; one that does not cannot, and no filter
recovers it. Both German word lists in this project have themselves discarded
case (`known_words()` is 0 capitalised of 668,580), so the rule has to be
written into the build rather than inherited from the data.

Tested against Leipzig-shaped fixture rows, never a download: the corpus is
219 MB and a test that fetched it would be a test nobody runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages/denckring-de-frequency/scripts"))

from build_frequency import bands  # noqa: E402

# `Tag`, `List`, `Power` and `Tower` are German nouns; their lowercase forms in
# a German corpus are another language's tokens. `gut` is not a noun and is
# genuinely lowercase German. `Gut` (an estate) is the noun, and both are real —
# which is why the rule keys on the noun list rather than on the word alone.
KNOWN = {"tag", "list", "power", "tower", "gut", "esel", "haus"}
NOUNS_LOWER = {"tag", "list", "power", "tower", "gut", "esel", "haus"} - {"gut"}


def test_a_noun_is_counted_only_from_capitalised_rows() -> None:
    table = bands([("Tag", 598), ("tag", 400)], KNOWN, NOUNS_LOWER)
    assert "tag" in table
    # 400 lowercase occurrences are English and must not reach the count.
    assert bands([("tag", 400)], KNOWN, NOUNS_LOWER) == {}


def test_a_non_noun_is_counted_only_from_lowercase_rows() -> None:
    assert "gut" in bands([("gut", 900)], KNOWN, NOUNS_LOWER)
    # `Gut` capitalised is a different word and is not this one's evidence.
    assert bands([("Gut", 900)], KNOWN, NOUNS_LOWER) == {}


def test_a_word_the_lexicon_does_not_know_is_dropped() -> None:
    assert bands([("Blockchain", 500)], KNOWN, NOUNS_LOWER) == {}


def test_short_forms_are_dropped() -> None:
    """`cd`, `kg` and `pi` are unit symbols and abbreviations, not words worth
    ranking. Three letters is the same floor `calculator_word` chose."""
    assert bands([("Tag", 5), ("PS", 900)], KNOWN | {"ps"}, NOUNS_LOWER | {"ps"}) == {"tag": 10}


def test_keys_are_lowercase_because_that_is_the_capability_s_convention() -> None:
    """0 capitals in English's 77,078 and French's 125,343, and `anagram`
    matches against the keys — capitalised keys would silently exclude every
    German noun. ADR 0038 records the cost: German prints nouns uncapitalised."""
    table = bands([("Tag", 5), ("Haus", 9)], KNOWN, NOUNS_LOWER)
    assert all(word == word.lower() for word in table)


def test_bands_run_from_10_to_60_with_larger_meaning_rarer() -> None:
    rows = [(f"Haus{i}", 1000 - i) for i in range(60)]
    known = {f"haus{i}" for i in range(60)}
    table = bands(rows, known, known)
    assert min(table.values()) == 10
    assert max(table.values()) == 60
    # The commonest word takes the lowest band.
    assert table["haus0"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_de_frequency_build.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_frequency'`.

- [ ] **Step 3: Write the build script's pure half**

```python
"""Build German frequency bands from a Leipzig Corpora Collection corpus.

Run by hand, not by any gate. It downloads 219 MB and writes one artefact.

    uv run python packages/denckring-de-frequency/scripts/build_frequency.py

The corpus is the Leipzig Corpora Collection's `deu_news_2023_1M`, whose
`*-words.txt` is `id <tab> word <tab> frequency`. Only that one member is read;
the sentences, sources and co-occurrence tables are never opened and never
redistributed.
"""

from __future__ import annotations

import gzip
import tarfile
import urllib.request
from pathlib import Path

CORPUS = "deu_news_2023_1M"
URL = f"https://downloads.wortschatz-leipzig.de/corpora/{CORPUS}.tar.gz"

#: Where the German Wiktionary chapter already caches its dump.
CACHE = Path.home() / ".cache" / "denckring-dumps"

#: Six bands, larger meaning *less* common — SCOWL's direction, which
#: `LanguagePack.graded_words` documents and `anagram` sorts ascending by. The
#: ceiling is 60 because `anagram`'s `max_size` is capped there. Identical to
#: `denckring-fr-data`'s, deliberately: this is the third use of one split and
#: re-deriving it would be a third chance to get the direction backwards.
BANDS = (10, 20, 30, 40, 50, 60)

#: `cd`, `kg` and `PS` are unit symbols and abbreviations. The same floor
#: `calculator_word` chose, and for the same reason.
MIN_LENGTH = 3


def bands(
    rows: list[tuple[str, int]], known: set[str], nouns_lower: set[str]
) -> dict[str, int]:
    """Frequency rows to a word-to-band table, applying the case rule.

    **ADR 0038 D3.** German capitalises common nouns, so a noun's German tokens
    are capitalised and its lowercase tokens belong to another language. Leipzig
    keeps that distinction; this project's own German word lists have thrown it
    away — `known_words()` is 0 capitalised of 668,580, and only `nouns()` keeps
    it. So the noun list is the case oracle:

    - a form whose lowercase is a known noun counts only when capitalised;
    - every other form counts only when lowercase.

    Without this the chapter reverts to the failure it exists to fix: a draft
    lowercased the keys before intersecting and `Wortspiel -> list power` came
    straight back, because lowercase English `list` and `power` appear in German
    news at 1M scale.

    `rows` may repeat a form; the largest count wins, since a corpus splits a
    word across capitalisations the tokeniser did not unify.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_de_frequency_build.py -q`
Expected: PASS, 6 tests.

- [ ] **Step 5: Prove the case tests red against a case-blind build**

Temporarily delete the two lines

```python
        if (low in nouns_lower) != form[:1].isupper():
            continue
```

and re-run. Expected: `test_a_noun_is_counted_only_from_capitalised_rows` and `test_a_non_noun_is_counted_only_from_lowercase_rows` **fail**. Restore them and confirm the suite is green again. A test written to pin a case rule that passes without the rule is worth nothing, and this project has shipped three such tests before review caught them.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-de-frequency/scripts/build_frequency.py tests/test_de_frequency_build.py
git commit -m "feat: the case rule for German frequency, tested before any download

ADR 0038 D3, and the decision this chapter turns on. German capitalises
common nouns, so a noun's German tokens are capitalised and its lowercase
tokens are another language's. Leipzig keeps that; this project's own German
lists have thrown it away — known_words() is 0 capitalised of 668,580 — so
nouns() is the case oracle and the rule lives in the build.

Tested against fixture rows, never a download: the corpus is 219 MB and a
test that fetched it is a test nobody runs. Proved red by deleting the rule.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 3: Fetch, build and vendor the table

**Files:**
- Modify: `packages/denckring-de-frequency/scripts/build_frequency.py`
- Create: `packages/denckring-de-frequency/src/denckring_de_frequency/data/graded_words.txt.gz`
- Create: `packages/denckring-de-frequency/src/denckring_de_frequency/data/metadata.json`
- Modify: `packages/denckring-de-frequency/src/denckring_de_frequency/__init__.py`

**Interfaces:**
- Consumes: `bands()` from Task 2.
- Produces: `graded_words() -> Mapping[str, int]`, an `lru_cache`d module function reading the gzipped table. Task 4's pack class wraps it.

- [ ] **Step 1: Add the download-and-write half to the script**

```python
def fetch(cache: Path = CACHE) -> Path:
    """The corpus archive, downloaded once and kept.

    Their terms forbid automated *queries* against the web service; this is the
    published download they offer, taken once. Cached so a rebuild does not ask
    again.
    """
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{CORPUS}.tar.gz"
    if not archive.exists():
        urllib.request.urlretrieve(URL, archive)
    return archive


def rows_from(archive: Path) -> list[tuple[str, int]]:
    """The `(form, count)` pairs from the archive's one words file.

    Read straight out of the tar rather than unpacking: the archive holds
    sentences, sources and two co-occurrence tables that this build never wants
    and that would cost 1 GB on disk to ignore.
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
    out = (
        Path(__file__).parent.parent
        / "src"
        / "denckring_de_frequency"
        / "data"
        / "graded_words.txt.gz"
    )
    with gzip.open(out, "wt", encoding="utf-8") as handle:
        for word in sorted(table):
            handle.write(f"{word}\t{table[word]}\n")
    print(f"{len(rows)} rows in, {len(table)} graded words, {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the build**

Run: `uv run python packages/denckring-de-frequency/scripts/build_frequency.py`
Expected: roughly `759,696 rows in, 101,296 graded words, 433,822 bytes`. The word count was measured on 2026-09-04; a few either way is a corpus revision, a large change is a bug in the case rule.

- [ ] **Step 3: Write `metadata.json` beside the table**

The shape `denckring-de-data` uses, with this build's own numbers substituted:

```json
{
  "counts": {
    "graded_words.txt.gz": 101296
  },
  "generated": "2026-09-04",
  "rows_read": 759696,
  "corpus": "deu_news_2023_1M",
  "source": "Leipzig Corpora Collection, CC BY - see LICENSE-LEIPZIG and scripts/build_frequency.py"
}
```

`rows_read` is not in the German lexical package's version and is added here on purpose: the ratio of rows in to words out is what the case rule changes, so a future rebuild that quietly loses the rule shows up as the same corpus yielding far more words.

Have `main()` write this file rather than hand-editing it, so the date and counts cannot drift from the artefact beside them.

- [ ] **Step 4: Add the reader to `__init__.py`**

```python
@lru_cache(maxsize=1)
def graded_words() -> Mapping[str, int]:
    """Word to frequency band, where **larger means less common** — SCOWL's
    direction, which `LanguagePack.graded_words` documents.

    Keys are lowercase, which is the capability's de-facto convention: English's
    77,078 and French's 125,343 carry 0 capitals between them, and `anagram`
    matches covers against these keys. German is the first language for which
    that loses information — a noun's capital is part of its spelling — and
    ADR 0038 records the cost rather than quietly changing the contract.
    """
    table: dict[str, int] = {}
    with gzip.open(GRADED_WORDS_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            word, _, band = line.rstrip("\n").partition("\t")
            if band:
                table[word] = int(band)
    return table
```

Add `gzip`, `from functools import lru_cache` and `from collections.abc import Mapping` to the imports, and `"graded_words"` to `__all__`.

- [ ] **Step 5: Verify**

Run: `uv run python -c "import denckring_de_frequency as f; t = f.graded_words(); print(len(t), t['esel'], t['haus'])"`
Expected: a count near 101,296 and two plausible bands.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-de-frequency/scripts/build_frequency.py \
        packages/denckring-de-frequency/src/denckring_de_frequency/__init__.py \
        packages/denckring-de-frequency/src/denckring_de_frequency/data/
git commit -m "feat: build and vendor the German frequency table

101,296 graded words, 434 KB gzipped, from Leipzig's deu_news_2023_1M — between
English's 77,078 and French's 125,343.

Only the archive's words file is read, straight out of the tar: the sentences,
sources and two co-occurrence tables are neither wanted nor unpacked, and none
of them is redistributed. The archive itself is cached, never vendored.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 4: The pack, and the four-way composition

**Files:**
- Modify: `packages/denckring-de-frequency/src/denckring_de_frequency/__init__.py`
- Modify: `packages/denckring-de-data/src/denckring_de_data/__init__.py` (the `pack()` factory)
- Create: `tests/test_de_frequency_pack.py`

**Interfaces:**
- Consumes: `graded_words()` from Task 3.
- Produces: `GermanFrequencyPack(GermanDataPack)` and `GermanWiktionaryFrequencyPack`, both declaring `GRADED_WORDS`.

**The composition problem, which the spec left open.** Three optional German distributions make four install combinations, and `pack()` currently branches two ways. The classes form a chain — `GermanWiktionaryPack(GermanDataPack)` — so the answer is two more subclasses and a four-branch factory. Explicit, no dynamic class creation: ADR 0030 already replaced a computed-capabilities probe with a named factory once, and the reason it gives — a reader should be able to see what a class does — applies just as much here.

- [ ] **Step 1: Write the failing test**

```python
"""The German pack composes three optional distributions.

`de` alone, plus frequency, plus Wiktionary, or all three — four combinations,
and the factory must name a class for each. Only the combinations this install
actually has can be asserted directly; the rest are asserted on the classes.
"""

from denckring.lang import get_pack


def test_the_installed_german_pack_has_graded_words() -> None:
    assert "lexicon.graded_words" in get_pack("de").capabilities


def test_graded_words_is_a_read_only_view() -> None:
    """The module function is `lru_cache`d and shared by every caller in the
    process; handing the dict out would let one caller's mutation corrupt it for
    all the others. English and French return `MappingProxyType` for this."""
    import pytest

    table = get_pack("de").graded_words()
    with pytest.raises(TypeError):
        table["esel"] = 1  # type: ignore[index]


def test_every_combination_declares_what_it_carries() -> None:
    from denckring_de_data import GermanDataPack
    from denckring_de_frequency import GermanFrequencyPack, GermanWiktionaryFrequencyPack
    from denckring_de_wiktionary import GermanWiktionaryPack

    assert "lexicon.graded_words" not in GermanDataPack.capabilities
    assert "lexicon.graded_words" not in GermanWiktionaryPack.capabilities
    assert "lexicon.graded_words" in GermanFrequencyPack.capabilities
    assert "lexicon.graded_words" in GermanWiktionaryFrequencyPack.capabilities
    # The richest one carries both distributions' capabilities, not one.
    assert "stress" in GermanWiktionaryFrequencyPack.capabilities
    assert "lexicon.nouns" in GermanFrequencyPack.capabilities


def test_anagram_generates_in_german() -> None:
    """The point of the chapter. `Lebensmittel` has a genuine single-word
    anagram, which is the case worth naming."""
    from denckring import apply, check

    text = apply("anagram", "Lebensmittel", lang="de")
    assert check("anagram", text, lang="de", source="Lebensmittel").satisfied
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_de_frequency_pack.py -q`
Expected: FAIL — `ImportError: cannot import name 'GermanFrequencyPack'`.

- [ ] **Step 3: Add the two pack classes**

In `denckring_de_frequency/__init__.py`:

```python
class GermanFrequencyPack(GermanDataPack):
    """German with a lexicon and frequency bands behind it."""

    capabilities: ClassVar[frozenset[str]] = GermanDataPack.capabilities | {GRADED_WORDS}

    def graded_words(self) -> Mapping[str, int]:
        return MappingProxyType(graded_words())
```

and, guarded, the combination with the Wiktionary pack:

```python
try:
    from denckring_de_wiktionary import GermanWiktionaryPack
except ImportError:  # pragma: no cover - depends on what is installed
    GermanWiktionaryFrequencyPack = GermanFrequencyPack
else:

    class GermanWiktionaryFrequencyPack(GermanWiktionaryPack):  # type: ignore[no-redef]
        """Everything German has: lexicon, pronunciations and frequency.

        Declared here rather than in `denckring-de-wiktionary` because that
        distribution must not learn about this one — a reader may install either
        without the other, and the dependency would make one of those installs
        impossible. This package imports it optionally instead, the same shape
        `denckring-de-data`'s own factory uses.
        """

        capabilities: ClassVar[frozenset[str]] = GermanWiktionaryPack.capabilities | {
            GRADED_WORDS
        }

        def graded_words(self) -> Mapping[str, int]:
            return MappingProxyType(graded_words())
```

Import `GRADED_WORDS` from `denckring.lang.base`, `ClassVar` from `typing`, `MappingProxyType` from `types`, and `GermanDataPack` from `denckring_de_data`. Add both class names to `__all__`.

- [ ] **Step 4: Teach the factory the four combinations**

Replace the body of `pack()` in `denckring_de_data/__init__.py`:

```python
def pack() -> GermanPack:
    """The best German pack this install can supply. The `de` entry point.

    A factory rather than a class, because three distributions carry German data
    under three licences and only one of them may register the language.
    `denckring/lang/__init__.py` raises `DuplicatePack` for a second `de` entry
    point — deliberately, so that no installer has to choose between packs — and
    ADR 0013 forbids merging their licences. A factory satisfies both: one entry
    point, and the richest pack whose data is installed wins.

    Four combinations, each naming a class rather than composing one at runtime.
    ADR 0030 replaced a computed-capabilities probe with a named factory once
    already, for a reason that still holds: a reader should be able to see what
    a class carries without running it.

    The subclasses are imported here rather than at module scope because this
    distribution does not depend on either of them — the dependencies run the
    other way.
    """
    try:
        from denckring_de_frequency import GermanFrequencyPack, GermanWiktionaryFrequencyPack
    except ImportError:
        GermanFrequencyPack = None  # type: ignore[assignment,misc]
        GermanWiktionaryFrequencyPack = None  # type: ignore[assignment,misc]
    try:
        from denckring_de_wiktionary import GermanWiktionaryPack
    except ImportError:
        # Not installed. A procedure wanting `phonemes` will raise
        # `MissingCapability` naming it, which is the honest failure rather than
        # a guessed pronunciation.
        return GermanFrequencyPack() if GermanFrequencyPack else GermanDataPack()
    if GermanWiktionaryFrequencyPack is not None:
        return GermanWiktionaryFrequencyPack()
    return GermanWiktionaryPack()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_de_frequency_pack.py -q`
Expected: PASS, 4 tests.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-de-frequency/src/denckring_de_frequency/__init__.py \
        packages/denckring-de-data/src/denckring_de_data/__init__.py \
        tests/test_de_frequency_pack.py
git commit -m "feat: the German pack composes three optional distributions

Three optional German distributions make four install combinations, and
pack() branched two ways. The classes are a chain — GermanWiktionaryPack
subclasses GermanDataPack — so the answer is two more subclasses and a
four-branch factory, each branch naming a class.

Not composed at runtime: ADR 0030 replaced a computed-capabilities probe
with a named factory once already, and its reason holds — a reader should be
able to see what a class carries without running it.

The combined class lives in de-frequency, not de-wiktionary, because that
distribution must not learn about this one: either is installable without
the other, and a hard dependency would make one of those installs
impossible.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 5: The remedy, the catalogue row, and the counters

**Files:**
- Modify: `src/denckring/core/errors.py`
- Modify: `src/denckring/data/catalogue.yaml` (the `anagram` row)
- Modify: `tests/test_errors.py`

**Interfaces:**
- Consumes: the installed `lexicon.graded_words` from Task 4.
- Produces: nothing new; this task makes the library's own claims true again.

- [ ] **Step 1: Write the failing test**

```python
def test_german_graded_words_now_names_the_extra_that_supplies_it() -> None:
    """`_PERMANENTLY_MISSING` carried `("de", "lexicon.graded_words")` citing
    ADR 0028, and its own comment anticipated this: "a future data chapter that
    lifts one is a one-line removal, not a guess." This is that chapter."""
    from denckring.core.errors import extra_for

    assert extra_for("de", "lexicon.graded_words") == "de-frequency"
    message = str(MissingCapability("anagram", "de", "lexicon.graded_words"))
    assert "pip install denckring[de-frequency]" in message


def test_the_french_ceiling_is_untouched() -> None:
    """French `stress` is permanent (ADR 0034 D2) and must stay permanent — this
    chapter lifts one ceiling, not the concept of a ceiling."""
    from denckring.core.errors import extra_for

    assert extra_for("fr", "stress") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_errors.py -q`
Expected: FAIL — `extra_for("de", "lexicon.graded_words")` returns `None`.

- [ ] **Step 3: Move the pair from one table to the other**

In `src/denckring/core/errors.py`, delete this line from `_PERMANENTLY_MISSING`:

```python
        ("de", "lexicon.graded_words"),  # ADR 0028: SCOWL ships in denckring-en-data only.
```

and add to `_SPECIALIST_EXTRAS`:

```python
    # Lifted from `_PERMANENTLY_MISSING` by ADR 0038. SCOWL still ships in
    # denckring-en-data alone, but German no longer needs it: the Leipzig Corpora
    # Collection supplies frequency directly, under CC BY, in its own
    # distribution.
    ("de", "lexicon.graded_words"): "de-frequency",
```

Update `_EXTRAS`' long comment, which currently cites German `graded_words` as an example of a permanent gap — that sentence is now false, and a false comment is a defect here.

- [ ] **Step 4: Add `de` to the `anagram` catalogue row**

In `src/denckring/data/catalogue.yaml`, the `anagram` row's `languages` reads `[en, fr]`. Change it to `[en, de, fr]`. Leave `requires` and `apply_requires` alone — they were already correct.

- [ ] **Step 5: Run the tests and the counters**

Run: `uv run pytest tests/test_errors.py tests/test_catalogue_corrections.py -q`, then `uv run denckring status` and `uv run denckring eval --all`.
Expected: tests pass; `status` unchanged at `156 · 131 · 122 · 122 · 25`; `eval --all` unchanged at `528 passed` (Task 7 adds cases).

- [ ] **Step 6: Commit**

```bash
git add src/denckring/core/errors.py src/denckring/data/catalogue.yaml tests/test_errors.py
git commit -m "feat: German graded words are no longer a permanent ceiling

_PERMANENTLY_MISSING carried ('de', 'lexicon.graded_words') citing ADR 0028,
and its own comment anticipated this: a future data chapter that lifts one is
a one-line removal, not a guess. This is that chapter, and it is that removal.

SCOWL still ships in denckring-en-data alone; German simply no longer needs
it. The remedy now names denckring[de-frequency], which supplies it.

anagram's row adds de to languages, which read [en, fr] while runs_in already
computed [en, de, fr] — the two fields differ on purpose (ADR 0029), but not
about this.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 6: The corpus figures, pinned

**Files:**
- Create: `tests/test_de_frequency_corpus.py`

- [ ] **Step 1: Write the test**

```python
"""The figures ADR 0038 argues from, pinned so they cannot drift into prose.

The same guard `tests/test_calculator_corpus.py` carries, and for the same
reason: a data package can be rebuilt, and a number in a document cannot notice.
"""

import denckring_de_frequency as freq
from denckring.lang import get_pack


def test_the_table_is_the_size_the_adr_claims() -> None:
    """101,296 measured 2026-09-04 on deu_news_2023_1M. A tolerance of 200
    absorbs a corpus revision without absorbing a change to the case rule, which
    would move this by tens of thousands."""
    assert abs(len(freq.graded_words()) - 101_296) <= 200


def test_it_sits_between_english_and_french() -> None:
    """77,078 and 125,343. Not a coincidence worth pinning for its own sake —
    it is the claim that German is now a first-class language for `anagram`."""
    import denckring_en_data as en
    import denckring_fr_data as fr

    assert len(en.graded_words()) < len(freq.graded_words()) < len(fr.graded_words())


def test_bands_run_the_direction_the_capability_documents() -> None:
    table = freq.graded_words()
    assert set(table.values()) <= {10, 20, 30, 40, 50, 60}
    # `und` is among the commonest German words; a rare noun is not.
    assert table["und"] == 10


def test_the_case_rule_survived_the_build() -> None:
    """The regression that matters. Every one of these is a German noun whose
    lowercase form is an English word; each must be present (from its
    capitalised German rows) and none may carry a common band earned by English
    tokens. `Power` measured band 10 at 1M — it is genuinely common in news
    German — so the assertion is on presence and plausibility, not rarity."""
    table = freq.graded_words()
    for word in ("tag", "list", "power", "tower"):
        assert word in table, word
    # `esel` is common enough to be in the table at all, which the OpenSubtitles
    # source also managed; the point is that it is here without English help.
    assert "esel" in table


def test_german_nouns_are_lowercased_in_the_keys() -> None:
    """The cost ADR 0038 accepts, asserted so it is not mistaken for a bug."""
    assert all(word == word.lower() for word in freq.graded_words())
    assert "Esel" not in freq.graded_words()


def test_the_pack_offers_the_same_table() -> None:
    assert len(get_pack("de").graded_words()) == len(freq.graded_words())
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_de_frequency_corpus.py -q`
Expected: PASS, 6 tests. If a figure is off by more than its tolerance, **do not widen the tolerance** — find what moved and correct the ADR, because these numbers are its argument.

- [ ] **Step 3: Commit**

```bash
git add tests/test_de_frequency_corpus.py
git commit -m "test: pin the figures ADR 0038 argues from

101,296 graded words, between English's 77,078 and French's 125,343, and the
case rule's survivors — tag, list, power, tower all present from their
capitalised German rows. The same guard test_calculator_corpus.py carries,
for the same reason: a data package can be rebuilt and a number in a document
cannot notice.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 7: German golden cases for `anagram`

**Files:**
- Modify: `src/denckring/eval/fixtures/golden/anagram.yaml`

- [ ] **Step 1: Verify every candidate before writing it down**

Run:

```bash
uv run python -c "
from denckring import apply, check
for source in ('Lebensmittel', 'Taschenrechner', 'Bundeskanzler'):
    text = apply('anagram', source, lang='de')
    print(source, '->', repr(text), check('anagram', text, lang='de', source=source).satisfied)
"
```

Write down only what this prints. A hand-invented anagram is exactly the plausible-looking value this project's notes warn about, and an anagram is easy to get subtly wrong.

- [ ] **Step 2: Add the cases**

Open `src/denckring/eval/fixtures/golden/anagram.yaml`, read the existing English cases to match their shape, and append German ones using the strings Step 1 printed. Include at least: one satisfying case (`Lebensmittel` and its single-word anagram), one where the letters do not match at all, and one where they match but the result is not German — so the fixture exercises both the letter check and the lexicon.

Give each `lang: de` at case level, the way `homoteleuton.yaml` does for its French cases.

- [ ] **Step 3: Check the negatives fail for their own reason**

Run:

```bash
uv run python -c "
from denckring import check
r = check('anagram', 'xyz abc', lang='de', source='Lebensmittel')
print([v.rule for v in r.violations])
"
```

Compare each violation list against its case name. Per the chapter 6 trap, a verify-first loop that checks only `satisfied` will accept a case that fails for the wrong rule.

- [ ] **Step 4: Run eval**

Run: `uv run denckring eval --all`
Expected: `122 procedures · N passed · 0 failed`, where N is 528 plus the cases added. Count them rather than adjusting the expectation.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/eval/fixtures/golden/anagram.yaml
git commit -m "test: German golden cases for anagram

Every string verified by running apply and check rather than invented — an
anagram is easy to get subtly wrong, and a plausible-looking value is the
dangerous kind. Negatives checked against their violation lists, not just
against satisfied.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 8: ADR 0038, and close out

**Files:**
- Create: `docs/adr/0038-german-frequency.md`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md` (untracked; edit, do not commit)

- [ ] **Step 1: Write ADR 0038**

Follow `docs/adr/0015-lexicon-capabilities.md` for tone: a real problem, a decision, and consequences that **admit costs**. Record D1 (the licence reading — quote both sentences of Leipzig's terms), D2 (a sixth distribution), D3 (the case rule) and D4 (the six-band split, unchanged).

Consequences must include, with their measured figures:

- proper nouns from news text reach the table — `Neck`, `Olpe`, `Benz`, `EZB` — and produce `Denckring → grind neck`. Filtering them needs a part-of-speech signal this distribution does not have.
- `graded_words` keys stay lowercase, so German output prints nouns uncapitalised: `list power` where German writes `List Power`. German is the first language for which the convention loses information.
- news register alone, where French takes `max(books, films)`.
- the rejected alternative: OpenSubtitles, zero capitals in 1,157,685 rows.
- the rejected alternative: Wiktionary sense count, Spearman −0.272 (fr) and −0.324 (en) against true frequency.

- [ ] **Step 2: Add the CI typecheck path**

In `.github/workflows/ci.yml`, the typecheck job runs `mypy --strict` over the workspace packages. Add `packages/denckring-de-frequency/src` to that list. Check whether any job installs specific extras and needs `de-frequency` adding too.

- [ ] **Step 3: Update the README**

The install block lists the extras; add `pip install denckring[de-frequency]` with a one-line description. The paragraph beginning "Without `[en]`… `apply anagram` runs at all — its search needs a word list graded by commonness" now understates: German has one too. Correct it.

`tests/test_readme.py` pins several prose counts; run it after editing.

- [ ] **Step 4: The whole gate, both projects, plus the release check**

```bash
uv run pytest -q
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src \
    packages/denckring-de-wiktionary/src packages/denckring-de-frequency/src
uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all
uv run denckring status
uv run mkdocs build --strict
cd apps/explorer && uv run ruff check && uv run ruff format --check \
    && uv run mypy --strict src tests && uv run pytest
```

Then confirm the sixth distribution builds and does not break packaging:

```bash
uv build --all-packages          # expect twelve artefacts now, not ten
uvx twine check dist/*
uv run pytest tests/test_packaging.py -q
```

- [ ] **Step 5: Update `CLAUDE.md`** — replace the "German `lexicon.graded_words` — investigated, NOT shipped" section with what shipped, keeping both measured negatives so nobody re-proposes them. Do not commit it; it is excluded from git.

- [ ] **Step 6: Commit**

```bash
git add docs/adr/0038-german-frequency.md CHANGELOG.md README.md .github/workflows/ci.yml
git commit -m "docs: ADR 0038, German frequency from the Leipzig Corpora Collection

Records the licence reading, the sixth distribution, and the case rule that
the chapter turns on. Consequences admit the costs: proper nouns from news
text reach the table, graded_words' lowercase keys print German nouns
uncapitalised, and the register is news alone where French takes
max(books, films).

Both rejected sources are recorded with their numbers so they are not
proposed again: OpenSubtitles has zero capitals in 1,157,685 rows, and
Wiktionary sense count correlates -0.272 (fr) / -0.324 (en) with true
frequency.

Assisted-by: Claude:claude-opus-5[1m]"
```
