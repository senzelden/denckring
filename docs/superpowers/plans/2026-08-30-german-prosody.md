# German Prosody — Tranche A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the German pack `syllables.heuristic`, taking German from 78 of 119 runnable rows to 89.

**Architecture:** German copies the two-layer shape English already has — the heuristic in core with no data files, a pronouncing dictionary in a distribution later. This plan is only the core layer: one method and one capability on `GermanPack`, plus German golden cases for the eleven rows that unblock. No new package, no data, no licence question.

**Tech Stack:** Python 3.11+, pydantic, pytest, hypothesis, mypy --strict, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-30-german-prosody-design.md`

## Global Constraints

- **The gate is four commands, and all four must pass before any commit:**
  `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`, `uv run ruff format --check .`
- **Anything touching a procedure also runs** `uv run denckring eval --all` and `uv run denckring status`.
- **`test_the_sdist_stays_small` fails locally and that is expected** — `undefined/queneau-seams.png` is untracked and unignored, so `uv build --sdist` swallows it. It passes in a clean worktree. Do not chase it and do not raise the bound.
- **`procedure_id` is a reserved test-argument name.** `tests/conftest.py` auto-parametrises it over every registered procedure; also writing `@pytest.mark.parametrize("procedure_id", ...)` is a hard duplicate-parametrization error. Name the argument `pid`.
- **Do not push.** Decided 2026-08-30: commits stay local until release. `git push` is not part of any step here.
- **Commit trailer is `Assisted-by: Claude:claude-opus-5[1m]`**, never `Co-Authored-By:`. Never add `Signed-off-by:`.
- **Comments explain why, not what, and cite ADRs by number.** A comment that has become false is treated as a defect here, not a nit.
- **Stage files by name.** A `git add -A` once swept `undefined/queneau-seams.png` into a commit.

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/lang/de.py` | Modify. Add `syllable_count` and declare `SYLLABLES_HEURISTIC`. The only production change in this plan. |
| `tests/test_syllables_de.py` | Create. Unit tests for the German heuristic, mirroring `tests/test_syllables.py`'s shape for English. |
| `src/denckring/eval/fixtures/golden/*.yaml` | Modify, eleven files. One German case per row that unblocks. |
| `CHANGELOG.md` | Modify. The `[Unreleased]` entry. |

---

### Task 1: The German syllable heuristic

**Files:**
- Modify: `src/denckring/lang/de.py`
- Test: `tests/test_syllables_de.py` (create)

**Interfaces:**
- Consumes: `denckring.lang.base.SYLLABLES_HEURISTIC`, `BasePack.fold_diacritics`.
- Produces: `GermanPack.syllable_count(word: str) -> tuple[int, bool]`, second element always `False`. `SYLLABLES_HEURISTIC` in `GermanPack.capabilities`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_syllables_de.py`:

```python
"""The German syllable heuristic, and the honesty of it.

Mirrors tests/test_syllables.py for English. The German heuristic is simpler
than the English one on purpose — see the docstring on GermanPack.syllable_count
and D2 in docs/superpowers/specs/2026-08-30-german-prosody-design.md.
"""

import pytest

from denckring.lang.base import SYLLABLES_DICTIONARY, SYLLABLES_HEURISTIC
from denckring.lang.de import GermanPack

CORE = GermanPack()


def test_core_german_declares_only_the_heuristic() -> None:
    assert SYLLABLES_HEURISTIC in CORE.capabilities
    assert SYLLABLES_DICTIONARY not in CORE.capabilities


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("Haus", 1),      # au is one nucleus
        ("Deich", 1),     # ei likewise
        ("zwölf", 1),     # folded to zwolf; one vowel run
        ("Katze", 2),     # the case English gets wrong: final -e is pronounced
        ("Blume", 2),
        ("Häuser", 2),    # äu folds to au and stays one nucleus
        ("Straße", 2),    # ß folds to ss; vowels unaffected
        ("Bahnhof", 2),
        ("Boxkämpfer", 3),
    ],
)
def test_the_heuristic_counts_german_syllables(word: str, expected: int) -> None:
    assert CORE.syllable_count(word)[0] == expected


@pytest.mark.parametrize(("word", "counted", "truth"), [("Museum", 2, 3), ("Familie", 3, 4)])
def test_a_vowel_sequence_across_a_morpheme_boundary_undercounts(
    word: str, counted: int, truth: int
) -> None:
    """Pinned as known behaviour, not discovered later as a bug.

    A vowel run is one nucleus, which is right for a diphthong and wrong for a
    sequence spanning a boundary: Museum is Mu-se-um and Familie is Fa-mi-li-e.
    This is exactly what ADR 0012's `exact` flag exists to declare, and it is the
    same class of error the English heuristic already ships with. If a future
    change makes these right, update the numbers — do not delete the test.
    """
    assert CORE.syllable_count(word)[0] == counted
    assert counted < truth


def test_the_heuristic_never_claims_to_be_exact() -> None:
    for word in ("Katze", "Haus", "Museum", "xyzq"):
        _, exact = CORE.syllable_count(word)
        assert exact is False


def test_the_heuristic_never_returns_less_than_one_for_a_word() -> None:
    for word in ("Angst", "Herbst", "Schnee"):
        count, _ = CORE.syllable_count(word)
        assert count >= 1


def test_an_empty_string_has_no_syllables() -> None:
    assert CORE.syllable_count("") == (0, False)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_syllables_de.py -q`
Expected: FAIL. `test_core_german_declares_only_the_heuristic` fails on the missing capability; the counting tests fail with `MissingCapability: ... requires the capability 'syllables.heuristic'`, raised by `BasePack.syllable_count`.

- [ ] **Step 3: Write the implementation**

In `src/denckring/lang/de.py`, add `import re` after `from __future__ import annotations`, add `SYLLABLES_HEURISTIC` to the `denckring.lang.base` import list (keep it alphabetical — it sits after `LETTER_SHAPES`), and add this module constant beside `_DESCENDERS`:

```python
#: Diphthongs need no entry here. German's are au, ei, ai, eu, äu and oi, and
#: every one is a run of adjacent vowels that this pattern already counts as a
#: single nucleus. Naming them would be a list that changes no result.
_VOWEL_GROUP = re.compile(r"[aeiouy]+")
```

Change the class docstring from "the same four capabilities as English" to "the same five capabilities as core English", then add the method:

```python
    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Estimate syllables from spelling. Never reports itself as exact.

        Count vowel groups, and stop. English's two other rules are deliberately
        not carried over, because both are wrong for German: a final "e" is
        pronounced (`Katze` is `ˈkat.sə`, two syllables), so there is no silent-e
        subtraction — and with no silent-e rule there is nothing for a `-le` rule
        to compensate for.

        The cost, and why the second element is always False: a vowel sequence
        spanning a morpheme boundary is one nucleus to this pattern and two to a
        speaker. `Museum` gives 2 where German says 3, `Familie` 3 where German
        says 4. ADR 0012's `exact` flag is what keeps that honest, and unlike
        English there is not yet a `denckring[de]` dictionary to replace it.
        """
        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        if not letters:
            return 0, False
        return max(len(_VOWEL_GROUP.findall(letters)), 1), False
```

Add `SYLLABLES_HEURISTIC` to the capability set:

```python
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, SYLLABLES_HEURISTIC}
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_syllables_de.py -q`
Expected: PASS, 15 tests (1 + 9 parametrised counts + 2 undercounts + 3 singles).

- [ ] **Step 5: Run the honesty suites, which have opinions about capabilities**

Run: `uv run pytest tests/test_requires_honesty.py tests/test_capabilities.py tests/test_apply_requires.py tests/test_prosody_robustness.py -q`
Expected: PASS. `test_requires_honesty.py` maps each capability to the methods that realise it (`"syllables.heuristic": ("syllable_count",)`) and checks that a pack declaring one implements it. If anything fails here it is telling you the declaration and the implementation disagree — fix the code, not the suite.

- [ ] **Step 6: Confirm the eleven rows now run in German**

Run:

```bash
uv run python -c "
from denckring.core.registry import all_procedures
from denckring.lang import get_pack
caps = set(get_pack('de').capabilities)
runs = [p for p in all_procedures().values() if all(c in caps for c in p.meta.requires)]
print(len(runs), 'of', len(all_procedures()))
"
```

Expected: `89 of 119`. It was 78 before this task.

- [ ] **Step 7: Run the full gate**

```bash
uv run pytest -q
uv run mypy --strict src tests
uv run ruff check .
uv run ruff format --check .
uv run denckring eval --all
uv run denckring status
```

Expected: `pytest` fails only `test_the_sdist_stays_small` (see Global Constraints). `eval --all` reports `119 procedures · 353 passed · 0 failed`. `status` is unchanged at `154 · 128 · 119 · 119 · 26` — it counts implemented rows, and these eleven were always implemented; what changed is the language they run in.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/lang/de.py tests/test_syllables_de.py
git commit -F - <<'MSG'
feat: German counts its own syllables

`GermanPack` inherited `BasePack.syllable_count`, which raises, so eleven rows
— every syllabic form in the catalogue — were unreachable in German. English
has had the same heuristic in core since batch 1; German simply never got one.

Simpler than English's, not more complex. Both of English's rules beyond
vowel-group counting are wrong here: a final "e" is pronounced (`Katze` is
`ˈkat.sə`), so the silent-e subtraction goes, and with it the `-le` rule that
existed only to compensate for it. German's diphthongs need no special case
either — au, ei, ai, eu, äu and oi are each a run of adjacent vowels, which the
pattern already counts as one nucleus.

The known cost is pinned by a test rather than left to be rediscovered: a vowel
sequence across a morpheme boundary undercounts, so `Museum` gives 2 where
German says 3 and `Familie` gives 3 where it says 4. `exact` is always False,
which is what ADR 0012's flag is for — and unlike English there is no
`denckring[de]` dictionary to replace the estimate yet.

German goes from 78 of 119 runnable rows to 89.

Assisted-by: Claude:claude-opus-5[1m]
MSG
```

---

### Task 2: German golden cases for the eight single-pattern rows

**Files:**
- Modify: `src/denckring/eval/fixtures/golden/syllable_count.yaml`, `haiku.yaml`, `senryu.yaml`, `tanka.yaml`, `cinquain.yaml`, `alexandrine.yaml`, `hendecasyllable.yaml`, `monosyllabic_prose.yaml`

**Interfaces:**
- Consumes: `GermanPack.syllable_count` from Task 1.
- Produces: nothing other tasks read. This is the eval gate, which CI runs as a gate of its own — a green `pytest` is a different claim from a green scoreboard.

A row that gains a language gets golden cases in it, or the language is reachable and
unproven. These eight all take `params: {}` except `syllable_count`, so the case is text
plus a verdict.

**Every syllable count below was verified against the Task 1 heuristic before this plan
was written.** Do not adjust the text without re-checking with:

```bash
uv run python -c "
from denckring.lang.de import GermanPack
p = GermanPack()
print(sum(p.syllable_count(w)[0] for _, w in p.word_spans('YOUR LINE HERE')))
"
```

Use real umlauts, never ASCII transliterations. `Bäume` folds to `baume` and counts 2;
`Baeume` counts 3, because `ae` is a separate vowel run. This bit me while drafting.

- [ ] **Step 1: Read the fixture format**

Run: `sed -n '1,30p' src/denckring/eval/fixtures/golden/pangram.yaml`

Each file has a top-level `procedure:` and `lang:`, then `cases:`. A case overrides the
file's language with its own `lang: de` — `pangram.yaml`'s `victor-jagt` case is the model.
**Add cases; never change the file-level `lang`.**

- [ ] **Step 2: Add two cases to `syllable_count.yaml`**

Append to its `cases:` list:

```yaml
  - name: silben-treffen-das-muster
    lang: de
    source: constructed example
    text: |-
      der Hund schläft
      die Katze
    params: { pattern: [3, 3] }
    satisfied: true
  - name: eine-zeile-zu-lang
    lang: de
    source: constructed counterexample
    text: |-
      der Hund schläft
      die Katze rennt sehr schnell
    params: { pattern: [3, 3] }
    satisfied: false
```

Counts: `der`1 + `Hund`1 + `schläft`1 = 3; `die`1 + `Katze`2 = 3; the long line is 6.

- [ ] **Step 3: Verify those two before writing any others**

Run: `uv run pytest tests/test_golden.py -k syllable_count -q`

`eval` has no per-row flag — it takes only `--all` and `--json`. The golden cases
are also pytest cases, and `-k` is how a single row is run.
Expected: every case passes, the two new ones included.

If a count disagrees, the heuristic is right and the fixture is wrong — Task 1 pinned the
heuristic's behaviour with tests. Fix the text, never the heuristic.

- [ ] **Step 4: Add the six single-pattern verse rows**

`haiku.yaml` (5-7-5):

```yaml
  - name: teich-und-frosch
    lang: de
    source: constructed example
    text: |-
      ein alter Teich dort
      ein Frosch springt in das Wasser
      das Wasser klingt hell
    params: {}
    satisfied: true
```

`senryu.yaml` (5-7-5, the same three verified lines reordered so the two rows do not carry
identical text):

```yaml
  - name: niemand-sagt-ein-wort
    lang: de
    source: constructed example
    text: |-
      das Wasser klingt hell
      und niemand sagt ein Wort mehr
      ein alter Teich dort
    params: {}
    satisfied: true
```

`tanka.yaml` (5-7-5-7-7):

```yaml
  - name: mond-ueber-dem-haus
    lang: de
    source: constructed example
    text: |-
      ein alter Teich dort
      ein Frosch springt in das Wasser
      das Wasser klingt hell
      der Mond steht über dem Haus
      und niemand sagt ein Wort mehr
    params: {}
    satisfied: true
```

`cinquain.yaml` (2-4-6-8-2):

```yaml
  - name: der-wind-im-schnee
    lang: de
    source: constructed example
    text: |-
      der Wind
      so kalt und klar
      der Wind zieht durch das Haus
      und trägt den Schnee bis an das Tor
      ganz still
    params: {}
    satisfied: true
```

`alexandrine.yaml` (twelve syllables in the line):

```yaml
  - name: zwoelf-silben
    lang: de
    source: constructed example
    text: der Wind zieht durch das Land und trägt den Schnee davon
    params: {}
    satisfied: true
```

`hendecasyllable.yaml` (eleven):

```yaml
  - name: elf-silben
    lang: de
    source: constructed example
    text: der Abend kommt und bringt uns die Stille mit
    params: {}
    satisfied: true
```

- [ ] **Step 5: Add `monosyllabic_prose.yaml`**

Every word must count 1. Verified per word: `Der`1 `Hund`1 `läuft`1 `und`1 `der`1 `Baum`1
`steht`1 — `äu` folds to `au`, one run.

```yaml
  - name: nur-einsilbige-woerter
    lang: de
    source: constructed example
    text: Der Hund läuft und der Baum steht
    params: {}
    satisfied: true
```

- [ ] **Step 6: Run the eval gate**

```bash
uv run denckring eval --all
uv run denckring status
```

Expected: `119 procedures · 362 passed · 0 failed` — 353 plus the nine cases added here.
`status` unchanged at `154 · 128 · 119 · 119 · 26`: it counts implemented rows, and these
were always implemented. What changed is the language they run in.

- [ ] **Step 7: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
```

Expected: only `test_the_sdist_stays_small` fails.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/eval/fixtures/golden/
git commit -F - <<'MSG'
test: golden cases in German for the eight single-pattern syllabic rows

A row that gains a language gets golden cases in it, or the language is
reachable and unproven. Every count here was checked against the heuristic
before the text was chosen, not after.

All constructed examples, marked as such. ADR 0018's provenance rules mean an
attestation claim needs a citation with a year, and these have none to make:
they exist to pin the arithmetic in a second language, not to document a
tradition.

Assisted-by: Claude:claude-opus-5[1m]
MSG
```

---

### Task 3: German cases for the three multi-part rows

**Files:**
- Modify: `src/denckring/eval/fixtures/golden/renga.yaml`, `haibun.yaml`, `arca_musarithmica.yaml`

**Interfaces:**
- Consumes: `GermanPack.syllable_count` from Task 1.
- Produces: nothing other tasks read.

Split from Task 2 because these three are not a single repeated line pattern, and a
reviewer could reasonably accept Task 2's fixtures while rejecting these. `renga` is linked
verse alternating 5-7-5 and 7-7 stanzas; `haibun` is prose with a haiku in it; and
`arca_musarithmica` is the only one of the eleven that takes real parameters rather than
`params: {}`.

- [ ] **Step 1: Read what each row actually requires**

```bash
sed -n '1,40p' src/denckring/eval/fixtures/golden/renga.yaml
sed -n '1,40p' src/denckring/eval/fixtures/golden/haibun.yaml
sed -n '1,40p' src/denckring/eval/fixtures/golden/arca_musarithmica.yaml
cat src/denckring/procedures/renga.py
cat src/denckring/procedures/haibun.py
```

This step is research, not typing. The English cases show the structure the German ones
must mirror, and `arca_musarithmica.yaml`'s `params:` block is multi-line where the other
ten are `{}` — copy its shape rather than guessing at it.

- [ ] **Step 2: Build each German case from verified lines**

These 5- and 7-syllable lines are already verified against the heuristic and can be reused:

| syllables | line |
|---|---|
| 5 | `ein alter Teich dort` |
| 5 | `das Wasser klingt hell` |
| 7 | `ein Frosch springt in das Wasser` |
| 7 | `der Mond steht über dem Haus` |
| 7 | `und niemand sagt ein Wort mehr` |

Any new line must be checked with the one-liner in Task 2 before it goes in the file.

- [ ] **Step 3: Verify each row on its own before moving to the next**

```bash
uv run pytest tests/test_golden.py -k "renga or haibun or arca_musarithmica" -q
```

Expected: all cases pass. Fix the fixture, never the heuristic.

- [ ] **Step 4: Run the eval and the full gate**

```bash
uv run denckring eval --all
uv run denckring status
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
```

Expected: `0 failed`; `status` unchanged; only `test_the_sdist_stays_small` fails.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/eval/fixtures/golden/
git commit -F - <<'MSG'
test: German cases for renga, haibun and the Arca Musarithmica

The three of the eleven that are not one repeated line pattern: renga alternates
stanza shapes, haibun mixes prose with verse, and the Arca is the only one of the
eleven taking real parameters. Split from the previous commit for that reason
rather than volume.

Lines reused from the cases already verified there, so the arithmetic is pinned
once and not re-derived per row.

Assisted-by: Claude:claude-opus-5[1m]
MSG
```

---

### Task 4: The record

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-08-30-german-prosody-design.md` (status line, and one correction)

**Interfaces:**
- Consumes: the measured figures from Tasks 1–3.
- Produces: nothing code reads.

No ADR. Tranche A adds no data source and makes no decision a future reader needs talked
out of — ADR 0012 already governs the heuristic/dictionary split and the spec's D1 and D2
carry the rest. **The ADR is owed by tranche B**, which has a licence and a source to
justify. Writing one here would be an ADR about having done the obvious thing.

- [ ] **Step 1: Add the `[Unreleased]` entry**

Under `## [Unreleased]` → `### Added` in `CHANGELOG.md`:

```markdown
- German counts syllables. `GermanPack` gains `syllables.heuristic`, which it never
  had — it inherited the raising stub, so every syllabic form in the catalogue was
  unreachable in German. Vowel-group counting, always reporting itself as estimated.
  Deliberately simpler than the English heuristic rather than a port of it: a final
  "e" is pronounced in German, so the silent-e rule and the `-le` rule that exists to
  compensate for it are both dropped, and the diphthongs need no special case because
  each is already a run of adjacent vowels. It undercounts a vowel sequence spanning a
  morpheme boundary — `Museum` gives 2 where German says 3 — which a test pins rather
  than leaves to be found later. German goes from 78 of 119 runnable rows to 89.
```

- [ ] **Step 2: Update the spec's status and correct one line in it**

Change `**Status:** draft` to
`**Status:** tranche A implemented 2026-08-30; tranche B not started`.

Then correct the Testing section. It says the round-trip budget "may move" and should be
re-measured. It cannot: `tests/test_round_trip.py` selects `procedure.meta.languages[0]`,
the row's editorial language, not a sweep over installed packs — so no row becomes newly
reachable there when a pack gains a capability. Replace that bullet with:

```markdown
- **`test_round_trip.py` is unaffected by tranche A**, which is worth stating because the
  draft of this spec assumed otherwise. It selects `procedure.meta.languages[0]` — the
  row's editorial language — rather than sweeping installed packs, so a pack gaining a
  capability adds no reachable row and cannot move the measured floor of 600.
```

- [ ] **Step 3: Confirm the docs still build strict**

```bash
uv run python scripts/build_docs.py
uv run mkdocs build --strict
```

Expected: builds clean. `CHANGELOG.md` is copied to the gitignored `docs/changelog.md` by
the build — edit the root file, never the copy.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md docs/superpowers/specs/2026-08-30-german-prosody-design.md
git commit -F - <<'MSG'
docs: record German syllable counting, and correct the spec on the round trip

No ADR. Tranche A adds no data source and makes no decision a future reader
needs talked out of — ADR 0012 already governs the heuristic/dictionary split.
The ADR is owed by tranche B, which has a licence and a source to justify.

The spec's Testing section said the round-trip budget might move and should be
re-measured. It cannot: test_round_trip.py selects meta.languages[0], the row's
editorial language, not the installed packs, so a pack gaining a capability adds
no reachable row. Corrected in place rather than left for someone to act on.

Assisted-by: Claude:claude-opus-5[1m]
MSG
```

---

## What this plan does not cover

**Tranche B** — `phonemes`, `stress`, `syllables.dictionary`, and the `denckring-de-phon`
distribution that supplies them, taking German from 89 to 117. Deliberately not planned here.

Its build script cannot be written to this document's standard yet. The spec's own
measurement section says the coverage figure belonging in B's ADR must come from the
dewiktionary dump, and the 90.8% measured from 639 tokens of this project's fixtures is not
that number. Planning B now would mean inventing the dump's structure and the script that
parses it — exactly the placeholder this skill forbids.

**B's plan comes after the dump is measured**, in that order: measure, write the ADR with the
real figure, then plan. Tranche A waits for none of it, which is why the spec made A
independently shippable.
