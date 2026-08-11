# German Language Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the twelve Batch 1 procedures to German, proving the language-pack capability interface and fixing the folding defect it exposes.

**Architecture:** Folding becomes a per-call parameter carried on a shared `DiacriticParams` base; glyph-shape questions stop folding entirely and move behind a new `exceeds_x_height` pack method; the German pack ships in core but registers through the `denckring.lang` entry-point group, so a third-party pack would install identically.

**Tech Stack:** Unchanged — Python 3.11+, uv, hatchling, Pydantic v2, PyYAML, Typer, pytest, Hypothesis, ruff, mypy strict.

## Global Constraints

Everything from the Batch 1 plan still applies, in particular: English API with no German identifiers; one module per procedure; `check` mandatory; no silent fallback; `satisfied == (score == 1.0)`; runtime dependencies remain exactly `pydantic>=2.7`, `pyyaml>=6.0`, `typer>=0.12`; `uv run pytest && ruff check && ruff format --check && mypy --strict src tests` all green before any commit; Conventional Commits.

New for this plan:

- **No data files.** German Batch 1 needs no lexicon, no hyphenation, no word list. If a task seems to need one, stop — it belongs to a later sub-project.
- **Every German golden case is CLI-verified before it is committed.** Where no public-domain German instance of a form exists, construct one and say so in `source`. Never present a constructed example as authentic.
- **German is `de` in data only.** No German identifiers, filenames aside (`lang/de.py`).

---

### Task 1: Entry-point pack discovery

**Files:**
- Modify: `src/denckring/lang/__init__.py`, `pyproject.toml`
- Test: `tests/test_lang_discovery.py`

**Interfaces:**
- Consumes: `LanguagePack`, `UnknownLanguage`.
- Produces: `get_pack` merges the `denckring.lang` entry-point group on first lookup; `register_pack` unchanged; new `installed_languages() -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lang_discovery.py
import pytest

from denckring.core.errors import UnknownLanguage
from denckring.lang import get_pack, installed_languages


def test_english_is_available_without_entry_point_metadata() -> None:
    assert get_pack("en").lang == "en"


def test_installed_languages_reports_what_is_loadable() -> None:
    assert "en" in installed_languages()


def test_unknown_language_still_raises() -> None:
    with pytest.raises(UnknownLanguage):
        get_pack("xx")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_lang_discovery.py -v`
Expected: FAIL — `ImportError: cannot import name 'installed_languages'`

- [ ] **Step 3: Implement discovery**

```python
# src/denckring/lang/__init__.py
"""Language pack lookup.

English is seeded directly so core never depends on its own installed metadata
being readable in order to find its own language. Every other pack — including
the German one that ships in this same wheel — arrives through the
`denckring.lang` entry-point group, which is exactly how a third-party pack
installs.
"""

from __future__ import annotations

from importlib.metadata import entry_points

from denckring.core.errors import UnknownLanguage
from denckring.core.protocol import LanguagePack
from denckring.lang.en import EnglishPack

ENTRY_POINT_GROUP = "denckring.lang"

_PACKS: dict[str, LanguagePack] = {"en": EnglishPack()}
_DISCOVERED = False


def _discover() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name in _PACKS:
            continue
        _PACKS[entry.name] = entry.load()()


def get_pack(lang: str) -> LanguagePack:
    """Return the installed pack for a language, or raise `UnknownLanguage`."""
    _discover()
    try:
        return _PACKS[lang]
    except KeyError:
        raise UnknownLanguage(str(lang)) from None


def register_pack(pack: LanguagePack) -> None:
    """Install a pack directly, bypassing entry-point discovery."""
    _PACKS[pack.lang] = pack


def installed_languages() -> list[str]:
    """Every language with a loadable pack, sorted."""
    _discover()
    return sorted(_PACKS)


__all__ = ["ENTRY_POINT_GROUP", "get_pack", "installed_languages", "register_pack"]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lang_discovery.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: discover language packs through an entry-point group"
```

---

### Task 2: `fold_diacritics` as a procedure parameter

**Files:**
- Modify: `src/denckring/core/text.py`, `src/denckring/core/base.py`
- Modify: the nine letter-comparing procedures under `src/denckring/procedures/`
- Test: `tests/test_fold_param.py`

**Interfaces:**
- Consumes: `letter_spans`.
- Produces:
  - `letter_spans(text, pack, *, fold: bool = True)`
  - `denckring.core.base.DiacriticParams` with `fold_diacritics: bool = True`
  - Nine `*Params` models inherit it: `Lipogram`, `Univocalic`, `Tautogram`, `Pangram`, `Heterogram`, `Palindrome`, `BeauPresent`, `Acrostic`, `Telestich`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fold_param.py
from denckring import check, get


def test_folding_on_by_default_treats_accents_as_the_base_letter() -> None:
    assert not check("lipogram", "café", forbidden="e").satisfied


def test_folding_off_treats_the_accented_form_as_a_different_letter() -> None:
    assert check("lipogram", "café", forbidden="e", fold_diacritics=False).satisfied


def test_the_parameter_is_exposed_in_the_json_schema() -> None:
    schema = get("lipogram").params_schema()
    assert "fold_diacritics" in schema["properties"]


def test_word_length_procedures_do_not_carry_the_parameter() -> None:
    assert "fold_diacritics" not in get("snowball").params_schema()["properties"]


def test_prisoners_constraint_does_not_carry_the_parameter() -> None:
    schema = get("prisoners_constraint").params_schema()
    assert "fold_diacritics" not in schema["properties"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_fold_param.py -v`
Expected: FAIL — `InvalidParams` on the unexpected `fold_diacritics` keyword.

- [ ] **Step 3: Add the `fold` argument to `letter_spans`**

```python
def letter_spans(text: str, pack: LanguagePack, *, fold: bool = True) -> list[tuple[int, str]]:
    """Every alphabetic character as `(offset, letter)`, lower-cased.

    With `fold` set, diacritics are stripped and `ß` expands to `ss`, so one
    source character can yield several letters sharing its offset. Without it,
    only case is normalised — `ä` stays `ä`.
    """
    spans: list[tuple[int, str]] = []
    for offset, ch in enumerate(text):
        if not ch.isalpha():
            continue
        letters = pack.fold_diacritics(ch) if fold else ch.lower()
        spans.extend((offset, letter) for letter in letters if letter.isalpha())
    return spans
```

- [ ] **Step 4: Add the shared params base**

In `src/denckring/core/base.py`:

```python
class DiacriticParams(BaseModel):
    """Mixed into every procedure that compares letters.

    Whether `Mädchen` belongs in an a-lipogram is an editorial decision, not a
    library constant — Perec's translators had to make it too. Carrying it as a
    parameter puts it in `params_schema()` and on the command line for free.
    """

    fold_diacritics: bool = Field(
        default=True,
        description="Treat accented letters as their base letter, and ß as ss.",
    )
```

- [ ] **Step 5: Inherit it in the nine procedures**

For each of `lipogram`, `univocalic`, `tautogram`, `pangram`, `heterogram`, `palindrome`,
`beau_present`, `acrostic`, `telestich`: change `class XParams(BaseModel)` to
`class XParams(DiacriticParams)`, import `DiacriticParams` from `denckring.core.base`,
and pass `fold=params.fold_diacritics` at every `letter_spans` call in that module. For
example, in `lipogram.py`:

```python
letters = letter_spans(text, pack, fold=params.fold_diacritics)
```

`palindrome`, `heterogram` and `acrostic` call `letter_spans` more than once — every call
in those modules takes the argument, including the ones on sub-strings.

Do **not** touch `snowball`, `reverse_snowball` or `prisoners_constraint`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_fold_param.py -v`
Expected: PASS, 5 tests

- [ ] **Step 7: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: make diacritic folding a per-call parameter"
```

---

### Task 3: Glyph shapes stop folding

**Files:**
- Modify: `src/denckring/lang/base.py`, `src/denckring/core/protocol.py`,
  `src/denckring/procedures/prisoners_constraint.py`
- Test: `tests/test_prisoners_constraint.py` (extend)

**Interfaces:**
- Produces: `LanguagePack.exceeds_x_height(ch: str) -> bool`, implemented concretely in `BasePack`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prisoners_constraint.py`:

```python
def test_an_accented_letter_breaks_the_x_height() -> None:
    # The acute rises above the x-height, so café violates the constraint even
    # though a folded "cafe" would not.
    assert not check("prisoners_constraint", "café").satisfied


def test_shape_questions_are_asked_of_the_written_character() -> None:
    report = check("prisoners_constraint", "café")
    assert report.violations[0].found == "é"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_prisoners_constraint.py -v`
Expected: FAIL — `café` currently folds to `cafe` and is wrongly satisfied.

- [ ] **Step 3: Add `exceeds_x_height` to `BasePack`**

```python
    def exceeds_x_height(self, ch: str) -> bool:
        """True when the written glyph rises above or drops below the x-height.

        Two independent reasons a character can fail: its base letter is an
        ascender or descender, or it carries a mark above. The second half is
        orthography-general — it catches ä, ö, ü and é without any pack naming
        them — so a pack only has to declare the letters its own alphabet adds.
        """
        if SHAPES not in self.capabilities:
            raise MissingCapability(DIRECT_CALL, self.lang, LETTER_SHAPES)
        lowered = ch.lower()
        if lowered in self.ascenders() | self.descenders():
            return True
        return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", lowered))
```

Use `LETTER_SHAPES` for both the guard and the error; the `SHAPES` name above is a typo
guard — write `if LETTER_SHAPES not in self.capabilities:`.

Add the method to the `LanguagePack` protocol in `core/protocol.py`:

```python
    def exceeds_x_height(self, ch: str) -> bool: ...
```

- [ ] **Step 4: Rewrite the checker to read raw characters**

```python
    def _check(self, text: str, pack: LanguagePack, params: PrisonersConstraintParams) -> Report:
        letters = [(offset, ch) for offset, ch in enumerate(text) if ch.isalpha()]
        violations = [
            Violation(
                rule="tall_or_deep_letter",
                offset=offset,
                found=ch,
                expected="a letter within the x-height",
            )
            for offset, ch in letters
            if pack.exceeds_x_height(ch)
        ]
        return self._report(
            good=len(letters) - len(violations),
            total=len(letters),
            violations=violations,
            metrics={"letters": float(len(letters)), "forbidden": float(len(violations))},
        )
```

Remove the now-unused `letter_spans` import from that module.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prisoners_constraint.py tests/strategies -v` then the full suite.
Expected: PASS. The existing English strategy alphabet contains no accents, so it is unaffected.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "fix: ask glyph-shape questions of the written character"
```

---

### Task 4: The German pack

**Files:**
- Create: `src/denckring/lang/de.py`
- Modify: `pyproject.toml` (entry point)
- Test: `tests/test_lang_de.py`

**Interfaces:**
- Produces: `denckring.lang.de.GermanPack`, registered as `de` in the `denckring.lang` group.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lang_de.py
import pytest

from denckring.core.errors import MissingCapability
from denckring.lang import get_pack, installed_languages
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS


def test_german_pack_is_discovered() -> None:
    assert "de" in installed_languages()
    assert get_pack("de").lang == "de"


def test_german_declares_the_same_four_capabilities_as_english() -> None:
    assert get_pack("de").capabilities == {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES}


def test_german_has_no_lexicon_or_syllables() -> None:
    pack = get_pack("de")
    with pytest.raises(MissingCapability):
        pack.syllables("Wetter")
    with pytest.raises(MissingCapability):
        list(pack.nouns())


def test_umlauts_are_vowels() -> None:
    assert {"ä", "ö", "ü"} <= get_pack("de").vowels()


def test_eszett_has_an_ascender() -> None:
    assert get_pack("de").exceeds_x_height("ß")


def test_umlauts_exceed_the_x_height() -> None:
    pack = get_pack("de")
    assert all(pack.exceeds_x_height(ch) for ch in "äöü")


def test_a_bare_vowel_stays_within_the_x_height() -> None:
    assert not get_pack("de").exceeds_x_height("a")


def test_the_alphabet_is_the_twenty_six_base_letters() -> None:
    assert get_pack("de").alphabet() == "abcdefghijklmnopqrstuvwxyz"


def test_folding_expands_eszett_and_strips_umlauts() -> None:
    pack = get_pack("de")
    assert pack.fold_diacritics("ß") == "ss"
    assert pack.fold_diacritics("Ä") == "a"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_lang_de.py -v`
Expected: FAIL — `UnknownLanguage: No language pack installed for 'de'`

- [ ] **Step 3: Write the pack**

```python
# src/denckring/lang/de.py
"""German. Ships in core, discovered through the entry-point group.

Batch 1 needs no lexicon and no hyphenation, so this pack carries no data and
core stays permissive. When German acquires a noun list, its licence decides
whether the data — not this module — moves behind an extra.
"""

from __future__ import annotations

from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS, BasePack

#: The 26 base letters. Traditional German pangrams satisfy exactly these — the
#: umlauts and ß are treated as decorated forms, not as alphabet members.
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VOWELS = frozenset("aeiouäöü")
#: ß is here because its written form carries an ascender. ä, ö and ü need no
#: entry: BasePack.exceeds_x_height catches any character with a mark above.
_ASCENDERS = frozenset("bdfhklt") | {"ß"}
_DESCENDERS = frozenset("fgjpqy")


class GermanPack(BasePack):
    lang: ClassVar[Lang] = "de"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES}
    )

    def alphabet(self) -> str:
        return _ALPHABET

    def vowels(self) -> frozenset[str]:
        return _VOWELS

    def ascenders(self) -> frozenset[str]:
        return _ASCENDERS

    def descenders(self) -> frozenset[str]:
        return _DESCENDERS
```

- [ ] **Step 4: Register the entry point**

In `pyproject.toml`:

```toml
[project.entry-points."denckring.lang"]
de = "denckring.lang.de:GermanPack"
```

Then reinstall so the metadata is regenerated: `uv sync --reinstall-package denckring`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lang_de.py -v`
Expected: PASS, 9 tests

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: add the German language pack"
```

---

### Task 5: Per-case fixture language and the declared-language invariant

**Files:**
- Modify: `src/denckring/eval/harness.py`, `tests/conftest.py`
- Test: `tests/test_invariants.py` (extend)

**Interfaces:**
- Produces: golden fixture cases may each carry `lang`, defaulting to the file-level value; new invariant `test_every_declared_language_has_a_golden_case`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_invariants.py`:

```python
def test_every_declared_language_has_a_golden_case(procedure_id: str) -> None:
    from conftest import load_golden_cases

    proc = get(procedure_id)
    covered = {c.lang for c in load_golden_cases() if c.procedure == procedure_id}
    missing = set(proc.meta.languages) - covered
    assert not missing, (
        f"{procedure_id} declares {sorted(missing)} in its catalogue row "
        f"but has no golden case in those languages"
    )
```

- [ ] **Step 2: Run it to verify it passes for now**

Run: `uv run pytest tests/test_invariants.py -k declared_language -v`
Expected: PASS — every procedure declares only `en` today, and every one has English
cases. It becomes load-bearing in Task 7, when the catalogue rows gain `de`.

- [ ] **Step 3: Make `lang` per-case in the harness**

In `golden_cases()`:

```python
    for path in sorted(GOLDEN_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        default_lang = data.get("lang", "en")
        for row in data["cases"]:
            cases.append(
                GoldenCase(
                    procedure=data["procedure"],
                    **{"lang": default_lang, **row},
                )
            )
```

- [ ] **Step 4: Make the same change in `tests/conftest.py`**

```python
        default_lang = data.get("lang", "en")
        for case in data["cases"]:
            cases.append(
                GoldenCase(
                    procedure=data["procedure"],
                    lang=case.get("lang", default_lang),
                    name=case["name"],
                    text=case["text"],
                    params=case.get("params", {}),
                    satisfied=case["satisfied"],
                    min_score=case.get("min_score"),
                    max_score=case.get("max_score"),
                )
            )
```

Also include the language in the test id so a German case is distinguishable:

```python
    def __str__(self) -> str:
        return f"{self.procedure}:{self.lang}:{self.name}"
```

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS. Test ids now read `lipogram:en:gadsby-opening`.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: allow per-case fixture languages and require one per declared language"
```

---

### Task 6: German golden cases for all twelve procedures

**Files:**
- Modify: all twelve `src/denckring/eval/fixtures/golden/*.yaml`

**Interfaces:** none new. This task is data.

Each file gains at least one `lang: de` case that is satisfied, and — where it reads
naturally — a German counterexample. Verified candidates, already checked against the
folding rules:

| Procedure | German case | Status |
|---|---|---|
| `pangram` | *Victor jagt zwölf Boxkämpfer quer über den großen Sylter Deich* | traditional; verified to cover a–z when folded |
| `palindrome` | *Ein Esel lese nie* | traditional; verified |
| `palindrome` | *Erika feuert nur untreue Fakire* | traditional; verified, use as a second case |
| `snowball` | *O du der Herr aller Dinge* | constructed; lengths 1–6 |
| everything else | constructed | must be CLI-verified before committing |

- [ ] **Step 1: Draft each German case and verify it through the CLI**

For every procedure, write the candidate to a file and run the checker. Example:

```bash
printf '%s' "Victor jagt zwölf Boxkämpfer quer über den großen Sylter Deich" > /tmp/de.txt
uv run denckring check pangram /tmp/de.txt --lang de
```

Expected: `satisfied (score 1.000)` and exit 0. **If a candidate does not verify, change
the candidate — never the checker.** A checker that has been loosened to accept a
convenient example has stopped being an eval.

- [ ] **Step 2: Add the verified cases to the fixture files**

Each case carries `lang: de`, a `source`, and honest attribution. A constructed example
says `constructed example` in its source; only *Victor jagt…*, *Ein Esel lese nie* and
*Erika feuert nur untreue Fakire* may be called traditional.

Shape, using `lipogram.yaml` as the pattern:

```yaml
  - name: <slug>
    lang: de
    source: constructed example
    text: <the German text>
    params: { forbidden: e }
    satisfied: true
```

- [ ] **Step 3: Run the eval and the suite**

Run: `uv run denckring eval --all` then `uv run pytest`
Expected: both green, with German cases visible in the scoreboard.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "test: add German golden cases for all twelve procedures"
```

---

### Task 7: Catalogue, documentation and the invariant going load-bearing

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`, `README.md`, `CHANGELOG.md`
- Create: `docs/adr/0009-folding-is-a-parameter.md`, `docs/adr/0010-packs-via-entry-points.md`

- [ ] **Step 1: Add `de` to the twelve implemented rows**

Change `languages: [en]` to `languages: [en, de]` on the twelve Batch 1 rows only. Leave
the catalogued-only rows alone — `alexandrine` stays `[fr]`, `denckring` and
`wechselsatz` stay `[de]`.

- [ ] **Step 2: Prove the invariant is load-bearing**

Temporarily delete one German case from `golden/lipogram.yaml` and run:

Run: `uv run pytest tests/test_invariants.py -k declared_language`
Expected: FAIL, naming `lipogram` and `['de']`. Restore the case and confirm it passes
again. Record the observed failure message in the commit message — this is the evidence
that the invariant does something.

- [ ] **Step 3: Write the two ADRs**

`0009-folding-is-a-parameter.md` — Context: whether `ä` counts as `a` has no single
right answer, and the same question arises for French `é` and English `café`. Decision:
`fold_diacritics` is a per-call parameter defaulting to true, carried on
`DiacriticParams`, excluded from procedures that count word length or read glyph shapes.
Consequences: the choice reaches the JSON schema and the CLI for free; two code paths
per letter-comparing procedure; shape questions must never fold, which is enforced by
`prisoners_constraint` not inheriting the model.

`0010-packs-via-entry-points.md` — Context: German needs no data, so gating it behind an
extra would gate nothing. Decision: German ships in core and registers through the
`denckring.lang` entry-point group; English is seeded directly so core does not depend on
its own metadata. Consequences: the third-party path is exercised by a real pack; when a
lexicon arrives, the *data* moves behind an extra, not the module; a broken install
surfaces as a missing language rather than a broken import.

- [ ] **Step 4: Update README and CHANGELOG**

README: German joins the install list as shipping in core, and the languages section
gains a sentence on `fold_diacritics`. CHANGELOG: an `Added` entry for the German pack,
entry-point discovery and the fold parameter, and a **`Fixed`** entry for the glyph
defect — English `café` now correctly violates `prisoners_constraint`, which is a
behaviour change a user could notice.

- [ ] **Step 5: Full acceptance run**

```bash
uv run pytest
uv run ruff format --check
uv run ruff check
uv run mypy --strict src tests
uv run denckring eval --all
uv run denckring status
uv run denckring check lipogram --lang de /tmp/de.txt
```

Expected: everything green, the scoreboard covering both languages.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: declare German support across the twelve Batch 1 procedures"
```

---

## Self-review notes

Spec coverage: fold policy → Task 2; glyph fix → Task 3; German pack → Task 4;
entry-point discovery → Task 1; per-case fixture language and the declared-language
invariant → Tasks 5 and 7; German fixtures → Task 6; catalogue, ADRs, changelog →
Task 7. Every acceptance criterion in the spec has a step that checks it.

Names used consistently: `fold_diacritics` (the parameter), `fold` (the `letter_spans`
argument), `DiacriticParams`, `exceeds_x_height`, `installed_languages`,
`ENTRY_POINT_GROUP`, `GermanPack`.

One ordering constraint worth stating: Task 3 must land before Task 6, or the German
prisoner's-constraint fixture would pass for the wrong reason — folding would hide the
`ß` and the umlauts it is meant to catch.
