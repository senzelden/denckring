# French Prosody (Chapter 6, Tranche B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `FrenchDataPack` the prosodic capabilities, and give every pack a line-level syllable seam, so the 23 syllabic rows run in French and coverage goes 80 → 103 of 121.

**Architecture:** Lexique 3.82 already ships in `denckring-fr-data`; this adds a second table from the same source (`nbsyll`, `phon`, `orthosyll`) plus an aspirated-*h* list from `frwiktionary`. The one change outside the French pack is a `line_syllables` method on `BasePack` whose default is today's per-word sum, so English and German are unchanged by construction, and which French overrides with the mute-e elision rules. A SAMPA→IPA table converts Lexique's transcription to the project's convention.

**Tech Stack:** Python 3.11, pydantic, pytest, hypothesis, `uv` workspaces, `mypy --strict`, ruff.

**Spec:** `docs/superpowers/specs/2026-08-31-french-design.md` — read it alongside this plan. Tranche A (F1, F2 minus prosody, the 10 lexicon rows) shipped 2026-08-31 as ADR 0032; this plan is F3, F4, F5 and the prosodic half of F2.

## Global Constraints

- **The gate is four commands, all of which must be green before any commit:**
  `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`,
  `uv run ruff format --check .`
- **Anything touching a data distribution runs the longer typecheck**, which is what CI
  runs: `uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src packages/denckring-de-wiktionary/src packages/denckring-fr-data/src`
- **Anything touching a procedure also runs:** `uv run denckring eval --all` and
  `uv run denckring status`. Expected before this chapter: `121 procedures · 439 passed · 0 failed` and `155 · 130 · 121 · 121 · 25`. The eval case count rises as golden cases land; the status line must not change, because this chapter implements no new row.
- **Any catalogue or count change also runs the explorer's own gate**, from inside the app:
  `cd apps/explorer && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests && uv run pytest` (expect 344 passed).
- **Commit trailer is `Assisted-by: Claude:claude-opus-5[1m]`.** Never `Co-Authored-By:`, never `Signed-off-by:`, never a `Claude-Session:` trailer. Author is `senzelden <sunless@gmx.net>`.
- **Do not push.** `origin/main` is pinned until release; commit freely.
- **Stage files by name.** Never `git add -A` — `undefined/` is untracked and must stay so.
- **The sdist bound is 1,200,000 bytes** and `tests/test_packaging.py` states the trade. Two new gzipped data files land under `packages/`, not under `src/`, so they do not count against it — but re-run `uv run pytest -q tests/test_packaging.py` after the build step and confirm rather than assume.
- **Comments explain why, not what, and cite ADRs by number.** A comment that has become false is a defect here, not a nit.
- **`procedure_id` is a reserved test-argument name** — `tests/conftest.py` auto-parametrises any test taking it, and re-parametrising it is a hard error. Name the argument `pid`.
- **French declares no `stress`.** Spec D2. The 18 accentual-metre rows stay blocked; 103 is the ceiling, not 121. Do not add `STRESS` to the French capability set to reach 121.

---

## What the go/no-go prototype established

Run 2026-09-01 against Racine's *Mithridate* and Hugo's *Hernani* (Gutenberg 27625, 9976). On lines interior to a speech block — a shared alexandrine split across speakers is a correct half-line count, not a counter error — the elision rules scored **89.7% of Racine's lines at exactly twelve, against a 97.4% ceiling once diérèse is chosen**; Hugo 80.2% against 85.9%. **The ceiling is what passed the seam**: the residual is concentrated in diérèse, a rule classical prosody specifies, rather than scattered.

Three data traps it cost, all of which this implementation will hit again:

1. **Lexique's SAMPA `@` is the nasal /ɑ̃/, not schwa.** `dans` → `d@`, `en` → `@`, `durant` → `dyR@`. Reading it as schwa strips a syllable off every nasal-final word — worth 15 points of accuracy, disguised as a plausible peak at 11 syllables. Schwa is `2`, which **also** spells /ø/: `de` and `deux` are both `d2`, and only the bare orthographic `-e` separates them. `les` is `le`, with no schwa at all.
2. **An elided proclitic is a consonant for the word in front of it.** Dropping `t'`, `d'`, `l'` from the token stream lets the preceding mute e see a vowel and elide — "ne t'attendais" loses a syllable. Worth 6 points.
3. **`orthosyll` judges a mute `-ent` and letter-run counting does not.** `chan-tent` is 2 against `nbsyll` 1, so the mute e shows; but `vient` strips to `vi`, whose single vowel run matches `nbsyll` 1, inventing a mute e it does not have. The letter-run fallback exists only for `vie`, `joie`, `an-née` — which `orthosyll` merges — and must never be applied to `-ent`.

The prototype itself is throwaway and is not in the repository. These findings are, and Task 6 encodes each as a named test.

---

## File Structure

| File | Responsibility |
|---|---|
| `packages/denckring-fr-data/src/denckring_fr_data/sampa.py` | **Create.** SAMPA→IPA table and `to_ipa`. One file because it is the one place French can go silently wrong (spec F0). |
| `packages/denckring-fr-data/scripts/build_lexicon.py` | **Modify.** Emit `syllables.txt.gz` from Lexique and `h_aspire.txt.gz` from the frwiktionary dump. |
| `packages/denckring-fr-data/src/denckring_fr_data/data/syllables.txt.gz` | **Create (generated).** `ortho\tnbsyll\tphon\torthosyll` per line. |
| `packages/denckring-fr-data/src/denckring_fr_data/data/h_aspire.txt.gz` | **Create (generated).** One aspirated-*h* headword per line. |
| `packages/denckring-fr-data/src/denckring_fr_data/elision.py` | **Create.** The mute-e rules and diérèse. Separate from `__init__.py` because it is the chapter's only real algorithm and wants to be readable on its own. |
| `packages/denckring-fr-data/src/denckring_fr_data/__init__.py` | **Modify.** Prosodic capabilities and the pack methods that serve them. |
| `src/denckring/lang/base.py` | **Modify.** `BasePack.line_syllables`, defaulting to today's per-word sum. |
| `src/denckring/procedures/syllable_count.py` | **Modify.** `line_syllables` delegates to the pack. |
| `tests/test_line_syllables.py` | **Create.** The seam, and that English and German are unchanged. |
| `tests/test_sampa_fr.py` | **Create.** The table against hand-checked words. |
| `tests/test_elision_fr.py` | **Create.** The three traps, each as a named test. |
| `src/denckring/eval/fixtures/golden/*.yaml` | **Modify.** French cases on the 23 syllabic rows. |
| `.github/workflows/ci.yml` | **Modify.** Extend the existing `french-without-data` job (ci.yml:167) to a syllabic row, and correct its now-false comment. |
| `docs/adr/0034-french-prosody.md` | **Create.** The record, with the measured figure and the diérèse cost. |

---

### Task 1: The SAMPA→IPA table

The test net first, before anything reads it (spec F0).

**Files:**
- Create: `packages/denckring-fr-data/src/denckring_fr_data/sampa.py`
- Test: `tests/test_sampa_fr.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SAMPA_TO_IPA: dict[str, str]`, `to_ipa(sampa: str) -> str`, `to_phonemes(sampa: str) -> list[str]`, `IPA_VOWELS: frozenset[str]`.

- [ ] **Step 1: Write the failing test**

```python
"""Lexique's SAMPA against hand-checked words.

`@` is the nasal /ɑ̃/ and `2` is /ø/ (and, after a bare orthographic -e, the
schwa). Getting those two wrong is worth fifteen points of line accuracy and
shows up as a plausible peak one syllable short, so they are pinned here.
"""

import pytest

from denckring_fr_data.sampa import IPA_VOWELS, to_ipa, to_phonemes


@pytest.mark.parametrize(
    ("sampa", "ipa"),
    [
        ("d@", "dɑ̃"),          # dans - @ is the nasal, not a schwa
        ("@", "ɑ̃"),            # en
        ("dyR@", "dyʁɑ̃"),      # durant
        ("d2", "dø"),           # de AND deux: Lexique spells both this way
        ("le", "le"),           # les - no schwa at all
        ("bEl", "bɛl"),         # belle
        ("fam", "fam"),         # femme
        ("Zwa", "ʒwa"),         # joie
        ("kaR@t", "kaʁɑ̃t"),    # quarante
        ("pRet@sj§", "pʁetɑ̃sjɔ̃"),  # prétentions
        ("f8ij@", "fɥijɑ̃"),    # fuyant
    ],
)
def test_sampa_converts_to_ipa(sampa: str, ipa: str) -> None:
    assert to_ipa(sampa) == ipa


def test_phonemes_split_one_symbol_at_a_time() -> None:
    """The nasal is one phoneme, not a vowel plus a combining tilde."""
    assert to_phonemes("d@") == ["d", "ɑ̃"]


def test_the_nasal_is_a_vowel_and_the_glides_are_not() -> None:
    """A glide carries no syllable of its own, which is the test
    `is_vowel_phoneme` exists to answer (ADR 0030)."""
    assert "ɑ̃" in IPA_VOWELS
    assert "ø" in IPA_VOWELS
    assert "j" not in IPA_VOWELS
    assert "w" not in IPA_VOWELS
    assert "ɥ" not in IPA_VOWELS


def test_every_symbol_lexique_uses_has_a_mapping() -> None:
    """An unmapped symbol must raise rather than pass through, because a
    silent pass-through is how a transcription scheme leaks into a count."""
    with pytest.raises(KeyError):
        to_ipa("d¤")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_sampa_fr.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'denckring_fr_data.sampa'`

- [ ] **Step 3: Write the table**

```python
"""Lexique 3.82's SAMPA, in the IPA this project uses everywhere else.

Lexique's alphabet is its own: `@` is the nasal /ɑ̃/ rather than a schwa, `§`
is /ɔ̃/, and `2`/`9` split /ø/ from /œ/. Reading `@` as a schwa costs fifteen
points of line accuracy and looks like a plausible one-syllable undercount, so
this table is tested against hand-checked words before anything reads it
(spec F0).
"""

from __future__ import annotations

#: Two-character sequences do not occur in Lexique's phon column, so a
#: character-by-character walk is complete.
SAMPA_TO_IPA: dict[str, str] = {
    # Oral vowels
    "a": "a", "A": "ɑ", "e": "e", "E": "ɛ", "i": "i", "o": "o", "O": "ɔ",
    "u": "u", "y": "y", "2": "ø", "9": "œ", "°": "ə",
    # Nasal vowels
    "@": "ɑ̃", "5": "ɛ̃", "1": "œ̃", "§": "ɔ̃",
    # Glides
    "j": "j", "w": "w", "8": "ɥ",
    # Consonants
    "b": "b", "d": "d", "f": "f", "g": "g", "k": "k", "l": "l", "m": "m",
    "n": "n", "N": "ŋ", "J": "ɲ", "p": "p", "R": "ʁ", "s": "s", "S": "ʃ",
    "t": "t", "v": "v", "z": "z", "Z": "ʒ", "G": "ɡ", "x": "x",
}

#: A glide is written with a vowel symbol in some schemes but carries no
#: syllable of its own, so it is not here. ADR 0030 is the reason this is a
#: property of the transcription rather than of the phoneme string.
IPA_VOWELS: frozenset[str] = frozenset(
    {"a", "ɑ", "e", "ɛ", "i", "o", "ɔ", "u", "y", "ø", "œ", "ə", "ɑ̃", "ɛ̃", "œ̃", "ɔ̃"}
)


def to_ipa(sampa: str) -> str:
    """Convert one Lexique transcription. An unmapped symbol raises.

    Passing an unknown symbol through would let a scheme leak silently into a
    syllable count, which is the defect ADR 0030 fixed twice in one day.
    """
    return "".join(SAMPA_TO_IPA[ch] for ch in sampa)


def to_phonemes(sampa: str) -> list[str]:
    """The transcription as a list of IPA phonemes.

    Lexique writes one symbol per phoneme, so the split is the walk itself and
    no re-segmentation of the IPA string is needed -- `d@` is ["d", "ɑ̃"], and
    the nasal stays one phoneme rather than a vowel plus a combining tilde.
    """
    return [SAMPA_TO_IPA[ch] for ch in sampa]
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `uv run pytest tests/test_sampa_fr.py -v`
Expected: PASS, 14 passed

- [ ] **Step 5: Commit**

```bash
git add packages/denckring-fr-data/src/denckring_fr_data/sampa.py \
        tests/test_sampa_fr.py
git commit -m "feat: Lexique's SAMPA in IPA, tested before anything reads it

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 2: The syllable table in the build script

**Files:**
- Modify: `packages/denckring-fr-data/scripts/build_lexicon.py`
- Create (generated): `packages/denckring-fr-data/src/denckring_fr_data/data/syllables.txt.gz`

**Interfaces:**
- Consumes: `Lexique382.zip` (the script already fetches it from `LEXIQUE_URL` when `--lexique` is omitted).
- Produces: a gzipped TSV, one line per orthographic form: `ortho\tnbsyll\tphon\torthosyll`, where the last column is the **segmented string** (`car-ros-se`), not a count — `syllables()` in Task 5 returns the segments and the count is `len(value.split("-"))`. `metadata.json` gains its row count.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_lang_fr_data.py` (create if absent):

```python
"""The shipped tables, checked for the shape the pack relies on."""

from denckring_fr_data import syllable_table


def test_the_syllable_table_carries_the_three_columns_the_rules_need() -> None:
    table = syllable_table()
    # nbsyll is the citation count, orthosyll judges a mute -ent, and phon
    # distinguishes `de` (d2, a schwa) from `les` (le, none).
    assert table["belle"] == (1, "bEl", "bel-le")
    assert table["les"] == (1, "le", "les")
    assert table["de"] == (1, "d2", "de")
    assert table["chantent"] == (1, "S@t", "chan-tent")
    assert table["vient"] == (1, "vj5", "vient")
    assert table["carrosse"][2] == "car-ros-se"


def test_a_homograph_keeps_its_most_frequent_reading() -> None:
    """`parent` is a noun of two syllables and a verb of one. The table holds
    one row per spelling, so it holds the commoner one and the pack is wrong
    about the other -- recorded in ADR 0034 rather than hidden."""
    assert syllable_table()["parent"][0] == 2
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: FAIL, `ImportError: cannot import name 'syllable_table'`

- [ ] **Step 3: Extend the build script**

In `build_lexicon.py`, beside the existing `WORDS`/`NOUNS`/`GRADED`/`GLOSSES` constants:

```python
SYLLABLES = DATA / "syllables.txt.gz"
```

and a writer, called from the same pass that reads Lexique's TSV:

```python
def write_syllables(rows: Iterator[dict[str, str]], path: Path) -> int:
    """One row per spelling: nbsyll, phon and the orthosyll segment count.

    Lexique carries several rows per spelling for homographs. Only one can be
    kept, because the pack is asked about a spelling and not about a reading,
    so the most frequent wins and ADR 0034 records that `parent` the verb is
    therefore counted as `parent` the noun.
    """
    best: dict[str, tuple[float, int, str, str]] = {}
    for row in rows:
        ortho = row["ortho"].strip().lower()
        if not ortho:
            continue
        try:
            nbsyll = int(float(row["nbsyll"]))
            freq = float(row["freqlivres"] or 0)
        except (ValueError, TypeError):
            continue
        if nbsyll <= 0:
            continue
        osyll = (row.get("orthosyll") or "").strip() or ortho
        previous = best.get(ortho)
        if previous is None or freq > previous[0]:
            best[ortho] = (freq, nbsyll, row["phon"], osyll)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for ortho in sorted(best):
            _, nbsyll, phon, osyll = best[ortho]
            handle.write(f"{ortho}\t{nbsyll}\t{phon}\t{osyll}\n")
    return len(best)
```

Then in `denckring_fr_data/__init__.py`:

```python
SYLLABLES_PATH = Path(str(files("denckring_fr_data") / "data" / "syllables.txt.gz"))


@lru_cache(maxsize=1)
def syllable_table() -> Mapping[str, tuple[int, str, str]]:
    """spelling -> (citation syllables, Lexique SAMPA, orthographic syllabation).

    The third element is the segmented spelling (`car-ros-se`), which serves two
    callers: `syllables()` returns its segments, and the mute-e rules compare
    its segment count against `nbsyll` to judge a final `-ent`.
    """
    table: dict[str, tuple[int, str, str]] = {}
    for line in _read(SYLLABLES_PATH):
        ortho, nbsyll, phon, osyll = line.split("\t")
        table[ortho] = (int(nbsyll), phon, osyll)
    return MappingProxyType(table)
```

- [ ] **Step 4: Regenerate the data and run the test**

```bash
uv run --project packages/denckring-fr-data python packages/denckring-fr-data/scripts/build_lexicon.py
uv run pytest tests/test_lang_fr_data.py -v
```
Expected: PASS. The script prints the new row count; confirm it is near 125,000, the size of the existing `words.txt.gz`.

- [ ] **Step 5: Confirm the sdist bound still holds**

Run: `uv run pytest -q tests/test_packaging.py`
Expected: PASS. The new file lives under `packages/`, not `src/`, so it should not count — confirm rather than assume.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-fr-data/scripts/build_lexicon.py \
        packages/denckring-fr-data/src/denckring_fr_data/__init__.py \
        packages/denckring-fr-data/src/denckring_fr_data/data/syllables.txt.gz \
        packages/denckring-fr-data/src/denckring_fr_data/data/metadata.json \
        tests/test_lang_fr_data.py
git commit -m "feat: French syllable counts, phonology and orthosyll from Lexique

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 3: The aspirated-*h* list

Spec F4. Vendored as data rather than as a rule in code, because it is a list of words and not a generalisation.

**Files:**
- Modify: `packages/denckring-fr-data/scripts/build_lexicon.py`
- Create (generated): `packages/denckring-fr-data/src/denckring_fr_data/data/h_aspire.txt.gz`

**Interfaces:**
- Consumes: the frwiktionary dump, via the existing `--dump PATH` flag. That flag is never fetched automatically — the dump is 876 MB and the script says so.
- Produces: `denckring_fr_data.h_aspire() -> frozenset[str]`.

- [ ] **Step 1: Write the failing test**

```python
def test_the_aspirated_h_list_separates_haricot_from_hotel() -> None:
    """Lexique gives `haricot` /aRiko/ and `hôtel` /otEl/ and cannot tell them
    apart; the elision rule needs the difference, so it comes from
    frwiktionary. The prototype's ad-hoc list missed `hais`, and "je hais"
    then elided wrongly -- inflected forms have to be in here too."""
    aspire = h_aspire()
    assert "haricot" in aspire
    assert "hais" in aspire
    assert "hauteur" in aspire
    assert "hôtel" not in aspire
    assert "homme" not in aspire
    assert "heure" not in aspire
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_lang_fr_data.py -k aspirated -v`
Expected: FAIL, `ImportError: cannot import name 'h_aspire'`

- [ ] **Step 3: Extract it in the same dump pass as the glosses**

frwiktionary marks an aspirated *h* with `{{h aspiré}}` in the pronunciation
line, and files inflected forms inline as senses marked
`{{S|verbe|fr|flexion}}` — **not** the way German files them under
`{{Grammatische Merkmale}}` outside the definitions block. Extracting French
the German way once yielded 2,026,448 "definitions" that were mostly
conjugation notes; check the language's own conventions rather than porting the
sibling's regex.

```python
H_ASPIRE = DATA / "h_aspire.txt.gz"
#: frwiktionary marks it on the pronunciation line. `\bh aspiré` rather than an
#: anchored match, because the template appears inside a larger line.
H_ASPIRE_RE = re.compile(r"\{\{h aspiré\}\}|\{\{asp\|fr\}\}")


def write_h_aspire(pages: Iterator[tuple[str, str]], path: Path) -> int:
    """Every headword frwiktionary marks as taking an aspirated h.

    Inflected forms are included: the elision rule is applied to the word as it
    appears in the line, and "je hais" needs `hais`, not only `haïr`.
    """
    found: set[str] = set()
    for title, body in pages:
        if not title.lower().startswith("h") or ":" in title:
            continue
        if H_ASPIRE_RE.search(body):
            found.add(title.lower())
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for word in sorted(found):
            handle.write(f"{word}\n")
    return len(found)
```

In `denckring_fr_data/__init__.py`:

```python
H_ASPIRE_PATH = Path(str(files("denckring_fr_data") / "data" / "h_aspire.txt.gz"))


@lru_cache(maxsize=1)
def h_aspire() -> frozenset[str]:
    """Words whose initial h blocks elision. Lexique cannot answer this."""
    return frozenset(_read(H_ASPIRE_PATH))
```

- [ ] **Step 4: Regenerate and run**

```bash
uv run --project packages/denckring-fr-data python packages/denckring-fr-data/scripts/build_lexicon.py --dump <path-to-frwiktionary-dump>
uv run pytest tests/test_lang_fr_data.py -v
```
Expected: PASS. Report the count in the commit message; a plausible figure is low thousands including inflections. **If the count is under 200 the regex did not match the dump's actual template** — inspect a known page (`haricot`) before going further rather than shipping a list that silently fails open.

- [ ] **Step 5: Commit**

```bash
git add packages/denckring-fr-data/scripts/build_lexicon.py \
        packages/denckring-fr-data/src/denckring_fr_data/__init__.py \
        packages/denckring-fr-data/src/denckring_fr_data/data/h_aspire.txt.gz \
        packages/denckring-fr-data/src/denckring_fr_data/data/metadata.json \
        tests/test_lang_fr_data.py
git commit -m "feat: the aspirated-h list, which Lexique cannot supply

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 4: The line seam

Spec F3. The only change to `src/` outside the French pack, and it must leave English and German byte-identical in behaviour.

**Files:**
- Modify: `src/denckring/lang/base.py`
- Modify: `src/denckring/procedures/syllable_count.py:15-31`
- Test: `tests/test_line_syllables.py`

**Interfaces:**
- Consumes: `BasePack.tokenize`, `BasePack.syllable_count`.
- Produces: `BasePack.line_syllables(self, line: str) -> tuple[int, int]` returning `(total, estimated)`. `denckring.procedures.syllable_count.line_syllables(text, pack)` keeps its signature and return type `list[tuple[int, int, int]]`; its five callers (`alexandrine`, `arca_musarithmica`, `haibun`, `hendecasyllable`, `renga`) are untouched.

- [ ] **Step 1: Write the failing test**

```python
"""The line seam, and that adding it changed nothing for English or German."""

from denckring.lang import get_pack
from denckring.procedures.syllable_count import line_syllables

FIXTURE = "the cat sat on the mat and thought of the wild mice\nthe dog ran home"


def test_the_default_is_the_per_word_sum() -> None:
    """English and German inherit today's behaviour by construction, which is
    the point of putting the default on the pack rather than in the procedure."""
    pack = get_pack("en")
    for line in FIXTURE.splitlines():
        expected = [pack.syllable_count(w) for w in pack.tokenize(line)]
        assert pack.line_syllables(line) == (
            sum(c for c, _ in expected),
            sum(1 for _, exact in expected if not exact),
        )


def test_english_and_german_line_counts_are_unchanged() -> None:
    """Asserted rather than assumed: this function is shared by five rows in
    three languages, and the seam exists to change exactly one of them."""
    assert line_syllables(FIXTURE, get_pack("en")) == [(0, 12, 0), (51, 4, 0)]


def test_a_pack_may_answer_for_a_whole_line() -> None:
    """The question `how long is this line` is asked of the thing that knows
    the language -- the move ADR 0030 made for `is_vowel_phoneme` after
    `assonance_constraint` answered it with CMUdict's convention."""

    class Counting(type(get_pack("en"))):  # type: ignore[misc]
        def line_syllables(self, line: str) -> tuple[int, int]:
            return (99, 1)

    assert line_syllables("anything at all", Counting()) == [(0, 99, 1)]
```

Before writing the expected tuples in `test_english_and_german_line_counts_are_unchanged`, run
`uv run python -c "from denckring.lang import get_pack; from denckring.procedures.syllable_count import line_syllables; print(line_syllables('the cat sat on the mat and thought of the wild mice\nthe dog ran home', get_pack('en')))"`
on the **current** tree and paste what it prints. The test's job is that the number does not move, so it must be seeded from the number before the change.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_line_syllables.py -v`
Expected: FAIL, `AttributeError: 'EnglishPack' object has no attribute 'line_syllables'`

- [ ] **Step 3: Add the default to `BasePack`**

```python
    def line_syllables(self, line: str) -> tuple[int, int]:
        """How many syllables the line has, and how many words were estimated.

        On the pack because the answer is a property of the language: French
        counts a final mute e as a syllable before a consonant and elides it
        before a vowel, so summing citation forms word by word undercounts
        systematically, and French verse is entirely syllable-counting. English
        and German want exactly this sum and inherit it unchanged (spec D3).
        """
        total = 0
        estimated = 0
        for word in self.tokenize(line):
            count, exact = self.syllable_count(word)
            total += count
            if not exact:
                estimated += 1
        return total, estimated
```

Then reduce `syllable_count.line_syllables` to a delegation, keeping its
signature and its docstring's promise about `estimated`:

```python
def line_syllables(text: str, pack: LanguagePack) -> list[tuple[int, int, int]]:
    """Per line: offset, syllable total, and how many words were estimated.

    The estimate count is what keeps a heuristic pack honest — every syllabic
    report carries it, and installing `denckring[en]` drives it to zero.

    The counting itself belongs to the pack (spec D3): French cannot be counted
    word by word, and the other two languages must not change to accommodate it.
    """
    measured: list[tuple[int, int, int]] = []
    for offset, line in line_spans(text):
        total, estimated = pack.line_syllables(line)
        measured.append((offset, total, estimated))
    return measured
```

Add `line_syllables` to the `LanguagePack` protocol in `src/denckring/core/protocol.py` beside `syllable_count`, so `mypy --strict` sees it on the protocol and not only on `BasePack`.

- [ ] **Step 4: Run the whole gate**

```bash
uv run pytest -q
uv run mypy --strict src tests
uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all   # expect 121 procedures · 439 passed · 0 failed
```
Expected: all green, and the eval count **unchanged** — this task adds no capability and must move no row.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/lang/base.py src/denckring/core/protocol.py \
        src/denckring/procedures/syllable_count.py tests/test_line_syllables.py
git commit -m "feat: a pack answers for a whole line, defaulting to the word sum

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 5: `FrenchDataPack`'s prosodic capabilities

**Files:**
- Modify: `packages/denckring-fr-data/src/denckring_fr_data/__init__.py`
- Test: `tests/test_lang_fr_data.py`

**Interfaces:**
- Consumes: `syllable_table()` (Task 2), `to_ipa`/`IPA_VOWELS` (Task 1).
- Produces: on `FrenchDataPack` — `syllable_count(word) -> tuple[int, bool]`, `syllables(word) -> list[str]`, `phonemes(word) -> list[str]`, `is_vowel_phoneme(p) -> bool`; capabilities gain `SYLLABLES`, `SYLLABLES_DICTIONARY`, `SYLLABLES_HEURISTIC`, `PHONEMES`.

- [ ] **Step 1: Write the failing test**

```python
"""French prosody on the pack. Not the line rules -- those are Task 6."""

import pytest

from denckring.core.errors import MissingCapability
from denckring.lang import get_pack


def test_a_word_in_lexique_is_exact_and_one_outside_it_is_not() -> None:
    pack = get_pack("fr")
    assert pack.syllable_count("belle") == (1, True)
    count, exact = pack.syllable_count("zzzzblorf")
    assert exact is False


def test_syllables_returns_the_orthographic_division() -> None:
    """French is the first pack that can honestly declare `syllables`: Lexique
    carries an orthographic syllabation, where German's transcriptions carry
    none and English's distribution declared the capability without one
    (ADR 0030, spec D5)."""
    assert get_pack("fr").syllables("carrosse") == ["car", "ros", "se"]


def test_phonemes_are_ipa_not_sampa() -> None:
    assert get_pack("fr").phonemes("dans") == ["d", "ɑ̃"]


def test_the_nasal_counts_as_a_vowel() -> None:
    """The trap that cost fifteen points in the prototype: `@` is /ɑ̃/, a
    vowel, and reading it as a schwa loses a syllable on every nasal-final
    word."""
    pack = get_pack("fr")
    assert pack.is_vowel_phoneme("ɑ̃") is True
    assert pack.is_vowel_phoneme("j") is False


def test_french_still_refuses_stress() -> None:
    """Spec D2. French has no lexical stress and declaring it to reach 121
    would be the defect ADR 0030 fixed twice in one day."""
    with pytest.raises(MissingCapability):
        get_pack("fr").rhyme_key("belle")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_lang_fr_data.py -v`
Expected: FAIL, `MissingCapability` on `syllable_count`

- [ ] **Step 3: Implement**

Add to `FrenchDataPack`'s `capabilities` frozenset: `SYLLABLES`,
`SYLLABLES_DICTIONARY`, `SYLLABLES_HEURISTIC`, `PHONEMES` — importing each from
`denckring.lang.base`. Then:

```python
    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Lexique's citation count, or a vowel-run estimate outside it.

        The count is the *citation* one: `femme` is one syllable here and
        frequently two in verse. The line rules, not this method, are where
        verse is answered -- spec D3.
        """
        entry = syllable_table().get(word.casefold())
        if entry is not None:
            return entry[0], True
        return max(len(_VOWEL_RUN.findall(word.casefold())), 1), False

    def syllables(self, word: str) -> list[str]:
        entry = syllable_table().get(word.casefold())
        if entry is None:
            raise KeyError(word)
        return entry[2].split("-")

    def phonemes(self, word: str) -> list[str]:
        entry = syllable_table().get(word.casefold())
        if entry is None:
            raise KeyError(word)
        return to_phonemes(entry[1])

    def is_vowel_phoneme(self, phoneme: str) -> bool:
        return phoneme in IPA_VOWELS
```

`_VOWEL_RUN` is the orthographic vowel-run pattern, defined here in
`__init__.py` beside its only use — the estimate for a word Lexique does not
carry. Task 6's `elision.py` defines its own for the mute-e rules; they are
deliberately not shared, because one answers "roughly how long is this unknown
word" and the other "does this known word end in a mute e", and a single
pattern serving both would tie two unrelated questions together.

- [ ] **Step 4: Run the test and the longer typecheck**

```bash
uv run pytest tests/ -q
uv run mypy --strict src tests packages/denckring-en-data/src \
  packages/denckring-de-data/src packages/denckring-de-wiktionary/src \
  packages/denckring-fr-data/src
```
Expected: PASS, and mypy clean.

- [ ] **Step 5: Measure the coverage move**

```bash
uv run python -c "
from denckring.core.registry import all_procedures
from denckring.lang import get_pack, installed_languages
for lang in installed_languages():
    caps = set(get_pack(lang).capabilities)
    runs = [p for p in all_procedures().values() if all(c in caps for c in p.meta.requires)]
    print(lang, len(runs), 'of', len(all_procedures()))
"
```
Expected: `fr 103 of 121`. **If it is not 103, stop and find out which row moved and why** before continuing — the spec's arithmetic is 80 + 23, and a different number means either a row was mis-classified in the spec or a capability was declared that should not have been.

- [ ] **Step 6: Commit**

```bash
git add packages/denckring-fr-data/src/denckring_fr_data/__init__.py \
        tests/test_lang_fr_data.py
git commit -m "feat: French declares syllables and phonemes, taking 80 to 103

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 6: The mute-e elision rules

The chapter's real algorithm, and the three traps as named tests.

**Files:**
- Create: `packages/denckring-fr-data/src/denckring_fr_data/elision.py`
- Modify: `packages/denckring-fr-data/src/denckring_fr_data/__init__.py` (the `line_syllables` override)
- Test: `tests/test_elision_fr.py`

**Interfaces:**
- Consumes: `syllable_table()` (Task 2), `h_aspire()` (Task 3).
- Produces: `latent_schwa(ortho, nbsyll, phon, orthosyll) -> tuple[int, bool]`, `count_line(line, table, aspire) -> tuple[int, int]`; `FrenchDataPack.line_syllables` overriding Task 4's default.

**`test_an_aspirated_h_blocks_elision` depends on Task 3 having landed.** Verified against
the prototype: with `hais` absent from the aspirated list, "je hais" scores 1 rather than
2, because `je`'s schwa elides across what it reads as a mute h. That is the whole reason
Task 3 exists, and this test is what proves the list is wired in.

- [ ] **Step 1: Write the failing test — one per trap, plus the rules**

```python
"""The mute-e rules, and the three traps the go/no-go prototype cost.

Each trap is its own test because each was found by hand-counting a line the
counter missed by one, and each is invisible to a green suite otherwise.
"""

from denckring_fr_data.elision import count_line
from denckring_fr_data import h_aspire, syllable_table


def line(text: str) -> int:
    return count_line(text, syllable_table(), h_aspire())[0]


def test_a_mute_e_counts_before_a_consonant_and_elides_before_a_vowel() -> None:
    assert line("une belle porte") == 5      # u-ne bel-le por-te, final e dropped
    assert line("une belle amie") == 5       # bel-l' a-mi-e


def test_a_mute_e_never_counts_at_the_end_of_a_line() -> None:
    assert line("la porte") == 2             # la por-te: the final e never counts


def test_the_nasal_is_not_a_schwa() -> None:
    """TRAP 1. Lexique writes /ɑ̃/ as `@`: `dans` is `d@` and `en` is `@`.
    Reading `@` as a schwa strips a syllable off every nasal-final word and
    shows up as a plausible peak one syllable short -- fifteen points."""
    assert line("dans le grand vent") == 4
    assert line("en fuyant") == 3


def test_de_and_deux_are_both_d2_and_only_the_spelling_separates_them() -> None:
    """TRAP 1, second half. `2` is /ø/ and, after a bare orthographic -e, the
    schwa. `les` is `le` and has no schwa at all."""
    assert line("de deux") == 2              # d' deux -> de counts, deux is 1
    assert line("les rois") == 2             # les is one syllable, not two


def test_an_elided_proclitic_is_a_consonant_for_the_word_in_front() -> None:
    """TRAP 2. Dropping `t'`, `d'`, `l'` from the token stream lets the
    preceding mute e see a vowel and elide -- six points."""
    assert line("ne t'attendais") == 4       # ne-t'at-ten-dais, the schwa holds
    assert line("dignes d'être") == 3        # di-gnes d'ê-tre, final e dropped


def test_orthosyll_judges_a_mute_ent_and_letter_runs_do_not() -> None:
    """TRAP 3. `chan-tent` is 2 against nbsyll 1, so the mute e shows; `vient`
    strips to `vi`, whose one vowel run matches nbsyll 1, inventing a mute e it
    does not have. The letter-run fallback exists for `vie`, `joie`, `an-née`,
    which orthosyll merges, and must never be applied to -ent."""
    assert line("ils chantent bien") == 4    # chan-tent
    assert line("il vient bien") == 3        # vient is one syllable
    assert line("la vie belle") == 4         # vi-e bel-le -> vi-e bel + final drop


def test_an_aspirated_h_blocks_elision() -> None:
    """The prototype's ad-hoc list missed `hais`, so "je hais" elided wrongly."""
    assert line("je hais") == 2              # je holds its schwa
    assert line("une heure") == 2            # mute h: u-n'heu-re, the schwa elides
```

Hand-count every expected number in this file against classical scansion before
writing it down, and if one disagrees with the implementation, **find out which
is wrong rather than adjusting the number to match the code**. A fixture loop
that checks only the boolean will accept a case that passes for the wrong
reason — the defect chapter 6 tranche A hit in `kangaroo_word`'s French negative.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_elision_fr.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'denckring_fr_data.elision'`

- [ ] **Step 3: Implement the rules**

```python
"""French verse counts a line, not a sequence of words (spec D3).

A final mute e is a syllable before a consonant, elides before a vowel or a
mute h, and never counts at the end of a line. Lexique gives citation forms --
`femme`, `une`, `belle` and `porte` are all one syllable there and frequently
two in verse -- so summing them undercounts systematically.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

VOWELS = frozenset("aeiouyàâéèêëîïôöùûüœæ")
_VOWEL_RUN = re.compile(r"[aeiouyàâéèêëîïôöùûüœæ]+")

#: Proclitics whose own vowel is already elided in the spelling. They carry no
#: syllable, but they are CONSONANTS for the word in front of them: in
#: "ne t'attendais" the schwa of `ne` cannot elide across the `t'`. Dropping
#: them from the token stream cost six points in the go/no-go prototype.
ELIDED_ZERO = frozenset({"l", "d", "j", "n", "m", "t", "s", "c", "qu"})
#: Same, but these carry syllables: `lorsqu'il` is lors-qu'il.
ELIDED_WORD = {
    "lorsqu": "lorsque", "puisqu": "puisque", "quoiqu": "quoique", "jusqu": "jusque",
}


def latent_schwa(ortho: str, nbsyll: int, phon: str, orthosyll: str) -> tuple[int, bool]:
    """(syllables excluding any mute e, whether a mute e is pending).

    Lexique's SAMPA `@` is the nasal /ɑ̃/, NOT a schwa -- `dans` is `d@`.
    Schwa is `2`, which also spells /ø/, so `de` and `deux` are both `d2` and
    only the bare orthographic -e separates them.
    """
    suffix = next((s for s in ("ent", "es", "e") if ortho.endswith(s)), None)
    if suffix is None:
        return nbsyll, False
    if suffix == "e" and phon[-1:] in ("2", "°"):
        # `le`, `je`, `que`: Lexique counted the schwa, so take it back out.
        return max(nbsyll - 1, 0), True
    if len(orthosyll.split("-")) > nbsyll:
        # `bel-le` against 1 shows the mute e; `sou-vent` against 2 does not.
        return nbsyll, True
    if suffix == "ent":
        # orthosyll already judged it. `vient` strips to `vi`, whose one vowel
        # run matches nbsyll 1, so the fallback below would invent a mute e.
        return nbsyll, False
    # orthosyll merges the mute e after a vowel (`vie`, `joie`, `an-née`), so
    # fall back to vowel letter-runs. `qu`/`gu` carry a silent u.
    stripped = ortho[: -len(suffix)].replace("qu", "k").replace("gu", "g")
    return nbsyll, len(_VOWEL_RUN.findall(stripped)) == nbsyll
```

`count_line` tokenises (splitting on apostrophes and hyphens, keeping the
proclitics as zero-syllable consonant-initial tokens), maps each token through
`latent_schwa`, then walks the result adding one for each pending schwa whose
successor is consonant-initial and which is not last. `starts_with_vowel`
consults `h_aspire()` for an initial `h`.

Then on `FrenchDataPack`:

```python
    def line_syllables(self, line: str) -> tuple[int, int]:
        """French counts a line, not a bag of words. Spec D3, ADR 0034."""
        return count_line(line, syllable_table(), h_aspire())
```

- [ ] **Step 4: Run the tests and the gate**

```bash
uv run pytest -q && uv run mypy --strict src tests packages/*/src
uv run ruff check . && uv run ruff format --check .
```
Expected: all green, and **English and German line counts still unchanged** — `tests/test_line_syllables.py` from Task 4 is the guard.

- [ ] **Step 5: Commit**

```bash
git add packages/denckring-fr-data/src/denckring_fr_data/elision.py \
        packages/denckring-fr-data/src/denckring_fr_data/__init__.py \
        tests/test_elision_fr.py
git commit -m "feat: the French mute-e rules, with the three traps pinned

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 7: Diérèse — the risky one, with a stop condition

The go/no-go measured 89.7% on Racine's interior lines against a **97.4% ceiling once diérèse is chosen**. Those 7.7 points are this task. Unlike every other task here, **the rule is not known in advance** — classical diérèse is etymological, and this task is a measurement loop, not an implementation.

**Files:**
- Modify: `packages/denckring-fr-data/src/denckring_fr_data/elision.py`
- Test: `tests/test_elision_fr.py`
- Create (throwaway, not committed): a scoring harness over Racine and Hugo

**Interfaces:**
- Consumes: `latent_schwa`, `count_line`.
- Produces: no new public name. `count_line` gains a diérèse pass internally.

- [ ] **Step 1: Rebuild the measurement harness**

Download Gutenberg 27625 (Racine, *Mithridate*) and 9976 (Hugo, *Hernani*) into a
scratchpad — **not** into the repository; ADR 0020 says a corpus is supplied by the
reader and never shipped. Score lines **interior to a speech block** (the first and
last line of a speech may be half of an alexandrine shared between speakers; Hugo's
unfiltered run has a 266-line spike at exactly 6, the caesura). Reproduce the baseline
before changing anything:

Expected baseline: Racine 89.7% at exactly twelve (n=1209), Hugo 80.2% (n=1139).
**If you do not reproduce those two numbers, stop** — the harness disagrees with the
one the go/no-go decision rests on, and the disagreement is the finding.

- [ ] **Step 2: Write the failing test for the clearest cases**

```python
def test_dierese_splits_a_glide_the_classical_line_counts_as_two() -> None:
    """`diadème` is di-a-dème in Racine and /djadɛm/ in Lexique; `prétentions`
    is pré-ten-ti-ons against /pʁetɑ̃sjɔ̃/. The count is estimated either way
    (spec D4) -- `extraordinaire` is four syllables or five depending on the
    poet -- so these pin the common cases, not a general rule."""
    assert line("Avec son diadème a remis son épée") == 12
    assert line("Sont les moindres sujets de nos divisions") == 12
```

- [ ] **Step 3: Implement a first rule and measure it**

Start from: a glide (`j`, `w`, `8` in SAMPA) preceded by a consonant **cluster**
ending in a liquid (`R`, `l`) is a diérèse; a glide after a single consonant is a
synérèse. Then measure. Record the Racine and Hugo figures after each variant.

- [ ] **Step 4: The stop condition**

**Accept** when Racine's interior figure reaches **≥ 95%** without Hugo's falling below
its 80.2% baseline. **Stop and report** if three rule variants fail to pass 93%: at that
point the remaining residue is editorial rather than mechanical, and the honest move is
to ship the count as `exact=False` at whatever it reaches and record the figure in ADR
0034 — not to keep tuning against the two texts, which is fitting to the test set.

Either way the number that goes in the ADR is the one measured here, and the ADR states
it as a limitation rather than a benefit.

- [ ] **Step 5: Commit**

```bash
git add packages/denckring-fr-data/src/denckring_fr_data/elision.py \
        tests/test_elision_fr.py
git commit -m "feat: dierese, taking Racine's interior lines from 89.7% to <measured>

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 8: Golden cases for the 23 rows

Spec F5. Built the way chapter 4 built the German ones: a verified line kit first, then the cases assembled from it.

**Files:**
- Modify: `src/denckring/eval/fixtures/golden/{alexandrine,arca_musarithmica,assonance_constraint,cinquain,clerihew,englyn,ghazal,haibun,haiku,hemeling,hendecasyllable,limerick,monosyllabic_prose,renga,rhyme_scheme,rondeau,senryu,spoonerism,syllable_count,tanka,terza_rima,triolet,villanelle}.yaml`

**Interfaces:** none — fixtures only.

- [ ] **Step 1: Build the verified line kit**

Collect French verse lines of known syllable count from public-domain sources, and
**run each through its own checker before writing it into a fixture**. A case that
passes for the wrong reason is the failure mode here: chapter 6 tranche A shipped a
`kangaroo_word` French negative that claimed "letters present but out of order" while
actually failing on a missing letter. **Compare the violation list against the case
name, not just `satisfied`.**

- [ ] **Step 2: Add cases, one row at a time**

Each case is a `lang: fr` entry in the existing file, in the shape
`alexandrine.yaml` already uses for its German case:

```yaml
  - name: alexandrin-de-racine
    lang: fr
    source: Jean Racine, Mithridate (1673), II.4
    text: Le temps n'est plus, Madame, où je pouvais me taire
    params: {}
    satisfied: true
  - name: onze-syllabes
    lang: fr
    source: constructed counterexample
    text: Le temps n'est plus où je pouvais me taire
    params: {}
    satisfied: false
```

At least one satisfying and one failing case per row, and the failing one must fail on
**the rule the name claims**.

- [ ] **Step 3: Run the eval after each file**

Run: `uv run denckring eval --all`
Expected: the pass count rises by the cases added, `0 failed`, and `121 procedures`.

- [ ] **Step 4: Run the round trip**

Run: `uv run pytest -q tests/test_round_trip.py`
Expected: PASS. Note this file tests each row in `meta.languages[0]`, which is English,
so it is **structurally blind to French defects** — it is a guard that nothing broke,
not evidence that French is right.

- [ ] **Step 5: Commit per batch of rows**

```bash
git add src/denckring/eval/fixtures/golden/<files>
git commit -m "test: French golden cases for the syllabic rows

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 9: Extend `french-without-data`, and ADR 0034

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `docs/adr/0034-french-prosody.md`
- Modify: `mkdocs.yml` (nav entry), `CHANGELOG.md`

- [ ] **Step 1: Extend the job that already exists**

**`french-without-data` is already in `ci.yml` at line 167** — it is not new. Today it
installs the core distribution alone and asserts that `lipogram` runs while `n_plus_7`
raises `MissingCapability` naming `lexicon.nouns`. Add the syllabic half, which is the
one this chapter makes reachable:

```yaml
          try:
              check('alexandrine', 'le temps n\'est plus', lang='fr')
          except MissingCapability as exc:
              assert 'syllables' in str(exc), exc
              print('fr-core: syllabic row raised as expected —', exc)
          else:
              raise SystemExit('alexandrine needs syllables, which this install lacks')
```

- [ ] **Step 2: Correct the job's comment, which this chapter makes false**

Its comment reads "ADR 0032 leaves 41 rows blocked in French". After this chapter that is
**18**, not 41. A comment that has become false is treated as a defect in this repository,
not a nit — several review rounds have turned entirely on one. Update it to cite ADR 0034
and the new figure.

- [ ] **Step 3: Write ADR 0034**

State: the line seam and why it lives on the pack; the measured alexandrine figure from
Task 7 **as a limitation, not a benefit** (`docs/adr/0015-lexicon-capabilities.md` is
the model for admitting a cost honestly); that the count is `exact=False` and why
(diérèse is not decidable without editorial intent — spec D4); that French declares
`syllables` and is the first pack that honestly can (D5); that `stress` is refused and
103 is the ceiling (D2); and the homograph cost from Task 2 (`parent` the verb is
counted as `parent` the noun).

Add the nav entry to `mkdocs.yml` after ADR 0033 and run `uv run mkdocs build --strict`.

- [ ] **Step 4: The full gate, plus the explorer**

```bash
uv run pytest -q && uv run mypy --strict src tests packages/*/src
uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
cd apps/explorer && uv run ruff check && uv run ruff format --check \
  && uv run mypy --strict src tests && uv run pytest
```
Expected: green everywhere; `status` still `155 · 130 · 121 · 121 · 25`; French coverage 103.

- [ ] **Step 5: Commit and merge the branch**

```bash
git add docs/adr/0034-french-prosody.md mkdocs.yml CHANGELOG.md .github/workflows/ci.yml
git commit -m "docs: ADR 0034, French prosody

Assisted-by: Claude:claude-opus-5[1m]"
git checkout main && git merge --no-ff -m "Merge: chapter 6 tranche B, French prosody" <branch>
```

Do **not** push.

---

## Self-Review

**Spec coverage.** F0 → Task 1. F1 (the build script) → Tasks 2 and 3. F2's prosodic
capabilities → Task 5. F3 (the line seam) → Task 4, with the French override in Task 6.
F4 (the aspirated-*h* list) → Task 3. F5 (golden cases) → Task 8. D2 (no `stress`) is a
global constraint and a test in Task 5. D3 → Tasks 4 and 6. D4 (`exact=False`) → Tasks 5
and 7. D5 (`syllables`) → Task 5. D6 (`graded_words`) **shipped in tranche A** and needs
no task here. The `french-without-data` job and the two measurements the spec asks the
ADR to stand on → Tasks 7 and 9.

**Known gap, stated rather than hidden.** Task 5's `syllables` needs the orthosyll
*string* where Task 2 stores a *count*. The fix is named inside Task 5 — store the
segmented string and derive the count from it — but if Task 2 is executed first and
literally, its test will need updating when Task 5 lands. Executing Task 2 with the
string column from the start avoids the rework.

**Type consistency.** `line_syllables` means two different things by design and this is
the plan's one real trap for a reader: `BasePack.line_syllables(line) -> tuple[int, int]`
takes **one line** and returns `(total, estimated)`, while
`denckring.procedures.syllable_count.line_syllables(text, pack) -> list[tuple[int, int, int]]`
takes **a whole text** and returns `(offset, total, estimated)` per line. The second calls
the first. The five callers of the second are untouched.
