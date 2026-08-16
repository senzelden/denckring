# German Lexicon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the German pack `lexicon.words` and `lexicon.nouns`, in a new `denckring-de-data` distribution, so five implemented procedures stop being English-only.

**Architecture:** `BasePack` already declares `is_word`, `nouns` and `noun_index`, each raising `MissingCapability`; `EnglishDataPack` overrides them. German gets a second implementation of that settled shape in a separate distribution built on Wikidata Lexemes (CC0). Before any of that is installable, core's German *entry point* must become a built-in *default*, because two entry points claiming `de` raise `DuplicatePack`.

**Tech Stack:** Python ≥3.11, uv workspace, hatchling, pytest, hypothesis, ruff, mypy --strict. Data from the Wikidata Query Service over SPARQL.

**Spec:** `docs/superpowers/specs/2026-08-16-german-lexicon-design.md`

## Global Constraints

- Python `>=3.11`. Core stays MIT and gains **no** new runtime dependency.
- The new distribution vendors its data. Neither installation nor use touches the network.
- Capability constants come from `denckring.lang.base`: `NOUNS = "lexicon.nouns"`, `WORDS = "lexicon.words"`.
- Noun list rule (ADR 0015, unchanged): purely alphabetic single tokens only, dictionary order, because N+7 indexes into it and a displacement must be a token the tokeniser returns whole.
- German normalisation: casefold for comparison, **keep umlauts and ß**. Never call `fold_diacritics` in the lexicon — it would collide `Bär` with `Bar`, and ADR 0009 makes folding a procedure parameter.
- Every command runs through uv: `uv run pytest`, `uv run ruff check`, `uv run mypy --strict`.
- `uv sync --extra en` is required before running the suite, or syllable-dependent tests fail for unrelated reasons.
- Do not implement `apply` for `anagram`, `n_plus_7`, `s_plus_7` or `slenderizing` in this plan. They are unblocked already and out of scope.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/lang/__init__.py` | Modify: German joins `_DEFAULTS` |
| `pyproject.toml` | Modify: drop the `de` entry point; add the `de` extra and workspace source |
| `docs/adr/0022-german-moves-to-a-default.md` | Create: amends ADR 0010 |
| `docs/adr/0023-the-german-lexicon.md` | Create: source, licence, normalisation, coverage |
| `packages/denckring-de-data/pyproject.toml` | Create: the distribution |
| `packages/denckring-de-data/LICENSE-WIKIDATA` | Create: CC0 dedication |
| `packages/denckring-de-data/README.md` | Create |
| `packages/denckring-de-data/scripts/build_lexicon.py` | Create: SPARQL queries + filtering, so the vendored files are reproducible |
| `packages/denckring-de-data/src/denckring_de_data/__init__.py` | Create: `GermanDataPack` |
| `packages/denckring-de-data/src/denckring_de_data/data/nouns.txt.gz` | Create: noun lemmas |
| `packages/denckring-de-data/src/denckring_de_data/data/words.txt.gz` | Create: membership oracle |
| `tests/test_lang_discovery.py` | Modify: German-is-a-default regression |
| `tests/test_lang_de_data.py` | Create: the pack's own tests |
| `src/denckring/data/catalogue.yaml` | Modify: five rows gain `de` |
| `src/denckring/eval/fixtures/golden/{charade,semordnilap,word_square,n_plus_7,s_plus_7}.yaml` | Modify: a German case each |

---

### Task 1: German becomes a built-in default

Core registers German through the `denckring.lang` entry-point group. `lang._install` refuses to choose between two packs claiming one language, so a second distribution claiming `de` raises `DuplicatePack` on the first `get_pack("de")` call. This is a live bug that blocks everything else; fix it before there is any data to install.

**Files:**
- Modify: `src/denckring/lang/__init__.py`
- Modify: `pyproject.toml` (remove the `[project.entry-points."denckring.lang"]` block)
- Create: `docs/adr/0022-german-moves-to-a-default.md`
- Test: `tests/test_lang_discovery.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `denckring.lang._DEFAULTS` contains `"de"`. Later tasks rely on an entry point named `de` from `denckring-de-data` overriding it.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lang_discovery.py`:

```python
def test_german_is_a_default_so_a_data_pack_can_override_it() -> None:
    """A data distribution claiming `de` must win, not collide.

    German shipped as an entry point (ADR 0010). Two entry points claiming one
    language raise DuplicatePack, so `pip install denckring[de]` would have
    broken on first use.
    """
    from denckring.lang import _DEFAULTS

    assert "de" in _DEFAULTS, "German must be a default for a data pack to override it"


def test_core_declares_no_language_entry_points() -> None:
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "pyproject.toml"
    manifest = tomllib.loads(root.read_text(encoding="utf-8"))
    groups = manifest["project"].get("entry-points", {})
    assert "denckring.lang" not in groups, (
        "core must not claim a language by entry point; a data pack could not override it"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_lang_discovery.py -q`
Expected: FAIL — `"de" not in _DEFAULTS`, and `denckring.lang` still present in entry-points.

- [ ] **Step 3: Make German a default**

In `src/denckring/lang/__init__.py`, add the import and extend `_DEFAULTS`:

```python
from denckring.lang.de import GermanPack
from denckring.lang.en import EnglishPack

#: The floor: always present, never dependent on installed metadata. German sits
#: here beside English so that `denckring-de-data` can override it the way
#: `denckring-en-data` overrides English. It was an entry point until a second
#: distribution claiming `de` proved that two entry points for one language
#: raise DuplicatePack. Amends ADR 0010.
_DEFAULTS: dict[str, LanguagePack] = {"en": EnglishPack(), "de": GermanPack()}
```

Update the module docstring's second sentence, which currently says German arrives through the entry-point group:

```python
"""Language pack lookup.

English and German are available as built-in *defaults* so core never depends on
its own installed metadata being readable in order to find its own languages.
Data distributions — `denckring[en]`, `denckring[de]` — arrive through the
`denckring.lang` entry-point group, which is exactly how a third-party pack
installs, and take precedence over the defaults they upgrade.

Precedence runs: explicitly registered pack, then entry point, then built-in
default. That ordering is what lets `denckring-en-data` upgrade English rather
than be shadowed by it.
"""
```

In `pyproject.toml`, delete these four lines:

```toml
# The German pack ships inside this wheel but is discovered exactly the way a
# third-party pack would be. See ADR 0010.
[project.entry-points."denckring.lang"]
de = "denckring.lang.de:GermanPack"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lang_discovery.py tests/test_lang_de.py -q`
Expected: PASS.

- [ ] **Step 5: Verify nothing else depended on the entry point**

Run: `uv sync --extra en && uv run pytest -q`
Expected: PASS, 1886 tests or more. `installed_languages()` must still report `de`.

- [ ] **Step 6: Write the ADR**

Create `docs/adr/0022-german-moves-to-a-default.md`:

```markdown
# 22. German is a built-in default, not an entry point

## Context

ADR 0010 registered the German pack through the `denckring.lang` entry-point group so
that a pack shipping inside the core wheel would take the same path a third-party pack
takes. That demonstration worked, and it stopped working the moment a German *data*
distribution became possible.

`lang._install` raises `DuplicatePack` when two entry points claim one language —
deliberately, because silently choosing would make answers depend on installation order.
Core claims `de` by entry point, so `pip install denckring[de]` would have raised on the
first `get_pack("de")` call.

English never had this problem: the core English pack is a built-in default, which is
precisely what lets `denckring-en-data` override it.

## Decision

German moves into `_DEFAULTS` beside English, and core declares no entry points at all.

## Consequences

`de` now behaves exactly like `en`: core provides the floor, a data distribution
upgrades it, and precedence resolves without a collision.

The demonstration ADR 0010 wanted is not lost but improved. The entry-point path is now
exercised by two genuinely external distributions, `denckring-en-data` and
`denckring-de-data`, rather than by core against itself — which is a stronger
demonstration than the one removed, because a same-wheel pack could never have proved
that precedence works.
```

- [ ] **Step 7: Commit**

```bash
git add src/denckring/lang/__init__.py pyproject.toml tests/test_lang_discovery.py docs/adr/0022-german-moves-to-a-default.md
git commit -m "fix: make German a default so a data pack can override it"
```

---

### Task 2: Generate and vendor the German lexicon

**Files:**
- Create: `packages/denckring-de-data/scripts/build_lexicon.py`
- Create: `packages/denckring-de-data/src/denckring_de_data/data/nouns.txt.gz`
- Create: `packages/denckring-de-data/src/denckring_de_data/data/words.txt.gz`
- Create: `packages/denckring-de-data/LICENSE-WIKIDATA`
- Test: `tests/test_lang_de_data.py`

**Interfaces:**
- Consumes: nothing.
- Produces: two gzipped UTF-8 files, one entry per line. `nouns.txt.gz` is sorted with `sorted()` (Python default ordering) and contains only strings matching `[A-Za-zÄÖÜäöüß]{2,}` starting with an upper-case letter. `words.txt.gz` is casefolded, one form per line.

- [ ] **Step 1: Write the build script**

Create `packages/denckring-de-data/scripts/build_lexicon.py`:

```python
"""Regenerate the vendored German lexicon from Wikidata Lexemes.

Committed so the data files are reproducible and diffable. CMUdict in the
English package is not, and a second opaque blob is not worth adding.

    python scripts/build_lexicon.py

Wikidata Lexemes are CC0: no attribution, no share-alike. See LICENSE-WIKIDATA.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "denckring-de-data/0.1 (https://github.com/senzelden/denckring)"
DATA = Path(__file__).resolve().parents[1] / "src" / "denckring_de_data" / "data"

#: German (Q188), noun (Q1084).
NOUN_LEMMAS = """
SELECT DISTINCT ?lemma WHERE {
  ?l dct:language wd:Q188 ; wikibase:lexicalCategory wd:Q1084 ; wikibase:lemma ?lemma .
}
"""

#: Every inflected form of every German lexeme, all lexical categories. Not
#: nouns alone: `charade` and `word_square` ask "is this a word", and a
#: noun-only oracle would reject `singen` and `rot`.
ALL_FORMS = """
SELECT DISTINCT ?rep WHERE {
  ?l dct:language wd:Q188 ; ontolex:lexicalForm ?f .
  ?f ontolex:representation ?rep .
}
"""

#: A noun the tokeniser returns whole: no spaces, no hyphens, no digits. ADR
#: 0015's rule for English, applied unchanged. Umlauts and ß are kept — folding
#: them here would collide `Bär` with `Bar`, and ADR 0009 makes folding a
#: procedure parameter rather than a property of the data.
SINGLE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")


def query(sparql: str) -> list[str]:
    url = f"{ENDPOINT}?{urllib.parse.urlencode({'query': sparql})}"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        payload = json.load(response)
    rows = payload["results"]["bindings"]
    return [next(iter(row.values()))["value"] for row in rows]


def write(path: Path, entries: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(entries))
    print(f"  {path.name}: {len(entries):,} entries", file=sys.stderr)


def main() -> int:
    lemmas = [w for w in query(NOUN_LEMMAS) if SINGLE_TOKEN.fullmatch(w) and w[:1].isupper()]
    nouns = sorted(set(lemmas))
    write(DATA / "nouns.txt.gz", nouns)

    forms = {w.casefold() for w in query(ALL_FORMS) if SINGLE_TOKEN.fullmatch(w)}
    forms.update(w.casefold() for w in nouns)
    write(DATA / "words.txt.gz", sorted(forms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run: `cd packages/denckring-de-data && uv run python scripts/build_lexicon.py`
Expected: roughly 178,000 nouns (188,947 lexemes, ~94% survive the single-token filter) and well over 1,399,865 forms — that figure is nouns only and is a lower bound. Record the actual counts; Task 4's ADR quotes them.

If the `ALL_FORMS` query times out, split it by lexical category and union the results locally. Do **not** reduce it to nouns only — that would reintroduce the bug this filter exists to avoid.

- [ ] **Step 3: Write the licence file**

Create `packages/denckring-de-data/LICENSE-WIKIDATA`:

```
The German lexicon in this distribution is derived from Wikidata Lexemes.

Wikidata's lexicographical data is released into the public domain under the
Creative Commons CC0 1.0 Universal Public Domain Dedication:

    https://creativecommons.org/publicdomain/zero/1.0/

CC0 imposes no attribution and no share-alike requirement. This file records the
provenance because the project records provenance, not because the licence
compels it.

Regenerate the vendored files with scripts/build_lexicon.py.
```

- [ ] **Step 4: Write the data tests**

Create `tests/test_lang_de_data.py`:

```python
"""The German lexicon's own invariants.

Skipped in full when `denckring[de]` is not installed, exactly as the English
data tests skip without `denckring[en]`.
"""

import re

import pytest

de_data = pytest.importorskip("denckring_de_data")

SINGLE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")


def test_noun_list_is_single_token_and_alphabetic() -> None:
    """ADR 0015's rule: N+7 walks this list and needs whole tokens."""
    nouns = de_data.noun_list()
    assert len(nouns) > 100_000
    offenders = [w for w in nouns if not SINGLE_TOKEN.fullmatch(w)]
    assert not offenders[:10], f"multi-token or non-alphabetic lemmas: {offenders[:10]}"


def test_noun_list_is_capitalised_as_german_nouns_are() -> None:
    nouns = de_data.noun_list()
    assert all(w[:1].isupper() for w in nouns[:1000])


def test_noun_list_is_in_dictionary_order() -> None:
    nouns = de_data.noun_list()
    assert list(nouns) == sorted(nouns)


def test_membership_covers_more_than_nouns() -> None:
    """A noun-only oracle would reject `singen` and `rot`."""
    known = de_data.known_words()
    assert "singen" in known
    assert "rot" in known
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lang_de_data.py -q`
Expected: SKIPPED — `denckring_de_data` is not importable yet. That is the correct failure at this point; Task 3 makes them run.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-de-data/scripts/build_lexicon.py \
        packages/denckring-de-data/src/denckring_de_data/data/ \
        packages/denckring-de-data/LICENSE-WIKIDATA \
        tests/test_lang_de_data.py
git commit -m "feat: vendor the German lexicon from Wikidata Lexemes"
```

---

### Task 3: The `GermanDataPack`

**Files:**
- Create: `packages/denckring-de-data/src/denckring_de_data/__init__.py`
- Test: `tests/test_lang_de_data.py` (extend)

**Interfaces:**
- Consumes: `nouns.txt.gz`, `words.txt.gz` from Task 2.
- Produces: `denckring_de_data.GermanDataPack`, plus module functions `noun_list() -> tuple[str, ...]`, `noun_positions() -> dict[str, int]`, `known_words() -> frozenset[str]`. Task 4's entry point loads `GermanDataPack`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lang_de_data.py`:

```python
def test_pack_declares_both_lexical_capabilities() -> None:
    from denckring.lang.base import NOUNS, WORDS

    pack = de_data.GermanDataPack()
    assert {NOUNS, WORDS} <= pack.capabilities


def test_is_word_knows_german() -> None:
    pack = de_data.GermanDataPack()
    assert pack.is_word("Katze")
    assert pack.is_word("katze"), "membership is case-insensitive"
    assert not pack.is_word("xqzzy")


def test_noun_index_finds_a_noun_and_rejects_a_non_noun() -> None:
    pack = de_data.GermanDataPack()
    assert pack.noun_index("Katze") is not None
    assert pack.noun_index("xqzzy") is None


def test_umlauts_are_kept_not_folded() -> None:
    """`fold_diacritics` would collide these two. ADR 0009 makes folding a
    procedure parameter, so the lexicon must not decide it for every caller."""
    pack = de_data.GermanDataPack()
    baer = pack.noun_index("Bär")
    bar = pack.noun_index("Bar")
    assert baer is not None and bar is not None
    assert baer != bar, "Bär and Bar must be distinct entries"


def test_eszett_is_kept() -> None:
    pack = de_data.GermanDataPack()
    assert pack.is_word("Straße")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_lang_de_data.py -q`
Expected: SKIPPED (module still absent).

- [ ] **Step 3: Write the pack**

Create `packages/denckring-de-data/src/denckring_de_data/__init__.py`:

```python
"""German lexicon data for denckring.

Installing this package gives the German pack the two lexical capabilities the
English pack has had since ADR 0015: `lexicon.words` and `lexicon.nouns`.
Nothing branches on whether it is present — the same procedures answer the same
calls, in a second language.

The data is Wikidata Lexemes, CC0. See LICENSE-WIKIDATA.
"""

from __future__ import annotations

import gzip
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    LETTER_SHAPES,
    NOUNS,
    TOKENS,
    WORDS,
)
from denckring.lang.de import GermanPack

NOUNS_PATH = Path(str(files("denckring_de_data") / "data" / "nouns.txt.gz"))
WORDS_PATH = Path(str(files("denckring_de_data") / "data" / "words.txt.gz"))

__version__ = "0.1.0"


def _read(path: Path) -> tuple[str, ...]:
    """Every line of a gzipped list.

    A truncated file raises rather than returning a short list: a short noun
    list makes N+7 quietly wrong, and a wrong answer is worse than an exception.
    """
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return tuple(line for line in handle.read().split("\n") if line)


@lru_cache(maxsize=1)
def noun_list() -> tuple[str, ...]:
    """Every noun lemma, in dictionary order, capitalised as German writes them."""
    return _read(NOUNS_PATH)


@lru_cache(maxsize=1)
def noun_positions() -> dict[str, int]:
    return {word.casefold(): index for index, word in enumerate(noun_list())}


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """Membership, from every inflected form of every German lexeme.

    Deliberately broad, in a way callers inherit: it answers "could this be a
    German word" rather than "is this in a dictionary of standard German", and
    procedures resting on it inherit that. The same caveat ADR 0015 recorded for
    English.
    """
    return frozenset(_read(WORDS_PATH))


class GermanDataPack(GermanPack):
    """German with a lexicon behind it."""

    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, NOUNS, WORDS}
    )

    def is_word(self, word: str) -> bool:
        return self._lemma(word) in known_words()

    def nouns(self) -> tuple[str, ...]:
        return noun_list()

    def noun_index(self, word: str) -> int | None:
        return noun_positions().get(self._lemma(word))

    @staticmethod
    def _lemma(word: str) -> str:
        """Casefold, and keep umlauts and ß.

        English strips to ASCII here. German must not: `fold_diacritics` would
        collide `Bär` with `Bar`, and ADR 0009 makes folding a parameter of the
        procedure rather than a property of the lexicon.
        """
        return "".join(ch for ch in word.casefold() if ch.isalpha())
```

- [ ] **Step 4: Install the package into the workspace and run the tests**

Run: `uv sync --extra en --extra de && uv run pytest tests/test_lang_de_data.py -q`
Expected: PASS. If the `de` extra does not exist yet, Task 4 adds it — install directly for now with `uv pip install -e packages/denckring-de-data`.

- [ ] **Step 5: Lint and typecheck**

Run: `uv run ruff check packages/denckring-de-data && uv run ruff format --check packages/denckring-de-data && uv run mypy --strict packages/denckring-de-data/src`
Expected: all clean.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-de-data/src/denckring_de_data/__init__.py tests/test_lang_de_data.py
git commit -m "feat: add GermanDataPack with lexicon.words and lexicon.nouns"
```

---

### Task 4: Package, wire and document the distribution

**Files:**
- Create: `packages/denckring-de-data/pyproject.toml`
- Create: `packages/denckring-de-data/README.md`
- Modify: `pyproject.toml` (root: `de` extra, uv source)
- Modify: `.github/workflows/ci.yml`
- Create: `docs/adr/0023-the-german-lexicon.md`
- Test: `tests/test_lang_discovery.py`

**Interfaces:**
- Consumes: `denckring_de_data.GermanDataPack` from Task 3.
- Produces: `pip install denckring[de]`; `get_pack("de")` returns a pack whose `capabilities` include `lexicon.nouns`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lang_discovery.py`:

```python
def test_the_german_data_pack_overrides_the_core_pack_when_installed() -> None:
    """The whole point of Task 1: an entry point beats a default, no collision."""
    pytest.importorskip("denckring_de_data")
    from denckring.lang.base import NOUNS

    pack = get_pack("de")
    assert NOUNS in pack.capabilities, "the data pack did not win over the core pack"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_lang_discovery.py -q`
Expected: FAIL — `get_pack("de")` returns the core `GermanPack`, which has no `lexicon.nouns`, because no entry point is declared yet.

- [ ] **Step 3: Write the distribution manifest**

Create `packages/denckring-de-data/pyproject.toml`:

```toml
[project]
name = "denckring-de-data"
version = "0.1.0"
description = "German lexicon data for denckring: word membership and a noun list"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
license-files = ["LICENSE-WIKIDATA"]
authors = [{ name = "senzelden", email = "senzelden@gmail.com" }]
classifiers = [
    "Intended Audience :: Science/Research",
    "Natural Language :: German",
    "Topic :: Text Processing :: Linguistic",
    "Typing :: Typed",
]
dependencies = ["denckring"]

[project.entry-points."denckring.lang"]
de = "denckring_de_data:GermanDataPack"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/denckring_de_data"]
```

- [ ] **Step 4: Wire the extra and the workspace source**

In the root `pyproject.toml`, extend the extras block:

```toml
[project.optional-dependencies]
# Exact syllable counts and rhyme, from the CMU Pronouncing Dictionary.
en = ["denckring-en-data"]
# Word membership and a noun list for German, from Wikidata Lexemes.
de = ["denckring-de-data"]
```

and the uv sources block:

```toml
[tool.uv.sources]
denckring = { workspace = true }
denckring-en-data = { workspace = true }
denckring-de-data = { workspace = true }
```

- [ ] **Step 5: Write the README**

Create `packages/denckring-de-data/README.md`:

```markdown
# denckring-de-data

German lexicon data for [denckring](https://github.com/senzelden/denckring):
word membership and an ordered noun list.

```console
pip install denckring[de]
```

Installing this gives the German pack `lexicon.words` and `lexicon.nouns`, which
is what `charade`, `semordnilap`, `word_square`, `n_plus_7` and `s_plus_7` need
in order to run in German. Without it those procedures raise
`MissingCapability` for `de`, exactly as they do for any unmet capability.

The data is derived from Wikidata Lexemes and is CC0 — no attribution, no
share-alike. Regenerate it with `scripts/build_lexicon.py`; the vendored files
are reproducible from that script alone.

Umlauts and ß are preserved rather than folded. `Bär` and `Bar` are different
words, and whether they should be treated alike is a decision ADR 0009 leaves to
the procedure, not to the lexicon.
```

- [ ] **Step 6: Add `de` to CI**

In `.github/workflows/ci.yml`, every `uv sync --extra en` becomes:

```yaml
      - run: uv sync --extra en --extra de
```

and the typecheck job's mypy target gains the new package:

```yaml
      - run: uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv sync --extra en --extra de && uv run pytest -q`
Expected: PASS, including `test_the_german_data_pack_overrides_the_core_pack_when_installed` and no `DuplicatePack`.

- [ ] **Step 8: Write the ADR**

Create `docs/adr/0023-the-german-lexicon.md`, substituting the real counts recorded in Task 2 Step 2 for `NOUN_COUNT` and `FORM_COUNT`:

```markdown
# 23. The German lexicon is Wikidata Lexemes

## Context

German shipped with four capabilities and no lexicon. Five implemented procedures —
`charade`, `semordnilap`, `word_square`, `n_plus_7`, `s_plus_7` — were English-only for
want of `lexicon.words` and `lexicon.nouns`.

The candidates each carry a licence the core would have had to answer for. igerman98 is
GPL-2/3; a Wiktionary dump is CC BY-SA; DeReWo is non-commercial. ADR 0013 already
quarantines data licences per distribution, so any of them was *possible* — but a
permissive one costs nothing to prefer.

## Decision

Wikidata Lexemes, CC0, vendored in `denckring-de-data`.

Coverage measured before the decision, not after: NOUN_COUNT noun lemmas surviving the
single-token filter, and FORM_COUNT inflected forms across all lexical categories for
membership. For comparison, CMUdict carries 135,166 entries.

Membership unions every lexical category, not nouns alone: `charade` and `word_square`
ask "is this a word", and a noun-only oracle rejects `singen` and `rot`.

Umlauts and ß are preserved. Casefolding is applied for comparison; `fold_diacritics` is
not, because it collides `Bär` with `Bar` and ADR 0009 makes folding a parameter of the
procedure.

## Consequences

The generating SPARQL is committed, so the vendored files are reproducible and a diff
between versions is readable. CMUdict is not, and this is the better precedent.

CC0 means no attribution or share-alike obligation reaches a user of `denckring[de]`.
`LICENSE-WIKIDATA` records the provenance anyway, because the project records
provenance.

The oracle is broad in the way ADR 0015 described for English: it answers "could this be
a German word", and procedures resting on it inherit that.
```

- [ ] **Step 9: Commit**

```bash
git add packages/denckring-de-data/pyproject.toml packages/denckring-de-data/README.md \
        pyproject.toml .github/workflows/ci.yml tests/test_lang_discovery.py \
        docs/adr/0023-the-german-lexicon.md uv.lock
git commit -m "feat: ship denckring-de-data as an installable extra"
```

---

### Task 5: Declare German on the five rows

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`
- Modify: `src/denckring/eval/fixtures/golden/charade.yaml`
- Modify: `src/denckring/eval/fixtures/golden/semordnilap.yaml`
- Modify: `src/denckring/eval/fixtures/golden/word_square.yaml`
- Modify: `src/denckring/eval/fixtures/golden/n_plus_7.yaml`
- Modify: `src/denckring/eval/fixtures/golden/s_plus_7.yaml`

**Interfaces:**
- Consumes: a `de` pack with `lexicon.words` and `lexicon.nouns` from Task 4.
- Produces: nothing later tasks depend on. This is the last task.

- [ ] **Step 1: Add `de` to one row and watch the invariant fail**

In `src/denckring/data/catalogue.yaml`, change `charade`'s languages:

```yaml
    languages: [en, de]
```

Run: `uv run pytest "tests/test_invariants.py::test_every_declared_language_has_a_golden_case[charade]" -q`
Expected: FAIL — "charade declares ['de'] in its catalogue row but has no golden case in those languages". This invariant is the acceptance criterion for the whole task; confirm it bites before relying on it.

- [ ] **Step 2: Add the German golden case for `charade`**

A charade splits a word into words: `Kleinod` → `klein` + `od`. Verify the parts are in the lexicon first:

```bash
uv run python -c "
from denckring.lang import get_pack
p = get_pack('de')
for w in ('klein', 'od', 'Kleinod'): print(w, p.is_word(w))
"
```

Pick a pair the oracle actually knows, then append to `src/denckring/eval/fixtures/golden/charade.yaml` under `cases:`:

```yaml
  - name: a-german-charade
    lang: de
    source: constructed example; the parts are words the lexicon knows
    text: "klein od"
    params:
      source: Kleinod
    satisfied: true
```

Adjust `text` and `params` to match the procedure's actual parameter names — read `src/denckring/procedures/charade.py` and the existing English cases in the same file rather than assuming.

- [ ] **Step 3: Run to verify it passes**

Run: `uv run pytest "tests/test_invariants.py::test_every_declared_language_has_a_golden_case[charade]" tests/test_golden.py -q`
Expected: PASS.

- [ ] **Step 4: Repeat for the remaining four rows**

For each of `semordnilap`, `word_square`, `n_plus_7`, `s_plus_7`: add `de` to `languages`, run the invariant to watch it fail, add a German golden case, run again to watch it pass.

German material for each, to be verified against the lexicon before use exactly as in Step 2:

- `semordnilap` — a word that is another word reversed. Try `Lager` / `Regal`; both are common nouns.
- `word_square` — a square whose rows and columns are all words. Build it from short words the oracle knows and confirm every row and column with `is_word` before recording the case.
- `n_plus_7` — displace each noun by seven in `nouns()`. Compute the expected output rather than guessing it:

```bash
uv run python -c "
from denckring.core.registry import get
p = get('n_plus_7')
print(p.check('...', lang='de', source='Die Katze schläft.'))
"
```

- `s_plus_7` — the same, with whatever displacement the procedure's parameters specify.

- [ ] **Step 5: Run the whole suite**

Run: `uv sync --extra en --extra de && uv run pytest -q`
Expected: PASS. Then confirm the scoreboard still reads sensibly: `uv run denckring status`.

- [ ] **Step 6: Verify German actually works end to end**

```bash
uv run denckring check n_plus_7 --lang de --source /dev/stdin <<< "Die Katze schläft."
```

Expected: a report, not `MissingCapability`.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/data/catalogue.yaml src/denckring/eval/fixtures/golden/
git commit -m "feat: declare German on the five lexicon-backed procedures"
```

---

## Self-Review

**Spec coverage.** Every section of the spec maps to a task: the entry-point fix (Task 1), the distribution (Tasks 2–4), data and provenance (Task 2), German normalisation (Task 3), catalogue changes (Task 5), error handling (Task 3 Step 3's `_read`, Task 4's override test), testing (spread across all five), and both ADRs (Tasks 1 and 4). Out-of-scope items are restated in the Global Constraints so an executor reading only this plan does not add them.

**Placeholders.** `NOUN_COUNT` and `FORM_COUNT` in the ADR are the one deliberate exception: they are measured in Task 2 Step 2 and the step says so. Task 5 Steps 2 and 4 deliberately instruct the engineer to verify words against the lexicon rather than trusting example words in this plan — the oracle's exact contents are not knowable until Task 2 runs, and recording a fixture with a word the lexicon lacks would produce a fixture that fails for the wrong reason.

**Type consistency.** `noun_list() -> tuple[str, ...]`, `noun_positions() -> dict[str, int]`, `known_words() -> frozenset[str]` are named identically in Task 2's Interfaces, Task 3's implementation and Task 3's tests. `GermanDataPack` is spelled the same in Task 3, Task 4's entry point and Task 4's manifest. `NOUNS`/`WORDS` come from `denckring.lang.base` throughout.
