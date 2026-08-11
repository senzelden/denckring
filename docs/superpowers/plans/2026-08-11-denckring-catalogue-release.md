# Catalogue Open-Data Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grow the catalogue from 31 rows to roughly 150 and make it publishable as a CC BY 4.0 dataset on its own terms.

**Architecture:** Three new required-or-defaulted fields on `Meta` (`family`, `aliases`, `attribution`), a validation suite that makes catalogue quality a test rather than a review, two discovery commands, and an export command producing the standalone release artifact.

**Tech Stack:** Unchanged.

## Global Constraints

Everything from the previous two plans still applies. New for this one:

- **Attribution discipline is the whole point.** `primary` means a named author, work and year the entry stands behind. If the origin is uncertain, the row says `reference` and names where the form is documented. **Never invent an inventor, a work or a date to fill a field.** A row that would need a fabricated `primary` is a `reference` row, and a form whose definition is uncertain does not go in at all.
- **Every row is complete when written.** No row lands missing a source, a definition, a prompt hint, a family or an attribution — the validation suite fails the build, so a half-filled row blocks everything.
- **No procedure gets implemented in this sub-project.** These are catalogue rows only; `implemented` stays at 12.
- Data tasks state target counts and rules rather than enumerating 120 rows inline. The content is the deliverable and is produced against the rules in each task; the validation suite is what checks it.

---

### Task 1: Schema fields and catalogue validation

**Files:**
- Modify: `src/denckring/core/protocol.py`, `src/denckring/data/catalogue.yaml`
- Test: `tests/test_catalogue_quality.py`

**Interfaces:**
- Produces: `Family`, `Attribution` type aliases; `Meta.family`, `Meta.aliases`, `Meta.attribution`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_catalogue_quality.py
"""Catalogue quality is a test, not a review."""

import pytest

from denckring.core import catalogue
from denckring.core.protocol import FAMILIES

ENTRIES = catalogue.load()


@pytest.mark.parametrize("meta", ENTRIES.values(), ids=list(ENTRIES))
def test_row_is_complete(meta) -> None:
    assert meta.names.get("en"), f"{meta.id} has no English name"
    assert meta.definitions.get("en"), f"{meta.id} has no English definition"
    assert meta.prompt_hints.get("en"), f"{meta.id} has no English prompt hint"
    assert meta.source.strip(), f"{meta.id} has no source"
    assert meta.family in FAMILIES, f"{meta.id} has family {meta.family!r}"


@pytest.mark.parametrize("meta", ENTRIES.values(), ids=list(ENTRIES))
def test_definition_is_a_sentence_not_a_label(meta) -> None:
    definition = meta.definitions["en"]
    assert len(definition.split()) >= 4, f"{meta.id}: {definition!r} is too terse to be useful"


def test_aliases_are_unique_across_the_catalogue() -> None:
    seen: dict[str, str] = {}
    for meta in ENTRIES.values():
        for alias in meta.aliases:
            key = alias.casefold()
            assert key not in seen, f"{meta.id} and {seen[key]} both claim the alias {alias!r}"
            seen[key] = meta.id


def test_aliases_never_collide_with_an_id() -> None:
    ids = set(ENTRIES)
    for meta in ENTRIES.values():
        clashes = {a for a in meta.aliases if a.casefold() in ids}
        assert not clashes, f"{meta.id} claims alias(es) {clashes} that are already ids"


def test_primary_attributions_name_a_year() -> None:
    """A primary attribution asserts a specific origin, so it must cite one."""
    for meta in ENTRIES.values():
        if meta.attribution == "primary":
            assert any(ch.isdigit() for ch in meta.source), (
                f"{meta.id} claims a primary attribution but its source names no year: "
                f"{meta.source!r} — use 'reference' if the origin is not established"
            )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_catalogue_quality.py -v`
Expected: FAIL — `ImportError: cannot import name 'FAMILIES'`

- [ ] **Step 3: Add the types**

In `src/denckring/core/protocol.py`, above `Meta`:

```python
Family = Literal[
    "letter",
    "word",
    "syntax",
    "form",
    "permutation",
    "procedural",
    "translation",
    "visual",
]
#: Runtime view of `Family`, for validation messages and the CLI.
FAMILIES: tuple[str, ...] = get_args(Family)

Attribution = Literal["primary", "reference", "traditional"]
```

Import `get_args` from `typing`. Then on `Meta`:

```python
    family: Family
    aliases: list[str] = Field(default_factory=list)
    attribution: Attribution
```

Place them after `source` so the YAML reads in a natural order.

- [ ] **Step 4: Backfill the 31 existing rows**

Every existing row gains `family` and `attribution`, and `aliases` where a form genuinely
travels under another name. Assignments for the twelve implemented rows:

| id | family | attribution | aliases |
|---|---|---|---|
| `lipogram` | letter | primary | — |
| `univocalic` | letter | reference | monovocalism |
| `tautogram` | letter | primary | — |
| `pangram` | letter | traditional | holalphabetic sentence |
| `heterogram` | letter | reference | isogram |
| `palindrome` | letter | traditional | — |
| `snowball` | letter | reference | rhopalic |
| `reverse_snowball` | letter | reference | melting snowball |
| `prisoners_constraint` | letter | primary | — |
| `beau_present` | letter | primary | beautiful present |
| `acrostic` | letter | traditional | — |
| `telestich` | letter | traditional | telestic |

For the nineteen catalogued-only rows: `n_plus_7` word/primary/alias `N+7`; `s_plus_7`
word/reference; `anagram` word/traditional; `larding` syntax/reference; `definitional_literature`
word/primary; `cut_up` procedural/primary; `fold_in` procedural/primary; `diastic`
procedural/primary; `mesostic` procedural/primary/alias `mesostich`; `syllable_count`
form/traditional; `alexandrine` form/traditional; `blank_verse` form/primary;
`rhyme_scheme` form/traditional; `sonnet` form/primary; `haiku` form/primary;
`terza_rima` form/primary; `denckring` permutation/primary; `proteus_verse`
permutation/primary; `wechselsatz` permutation/primary.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_catalogue_quality.py -v`
Expected: PASS. If `test_primary_attributions_name_a_year` fails on a row, that row's
attribution is wrong — change the attribution to `reference`, never the test.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: add family, aliases and attribution to catalogue entries"
```

---

### Task 2: Discovery commands

**Files:**
- Modify: `src/denckring/cli.py`
- Test: `tests/test_cli_search.py`

**Interfaces:**
- Produces: `denckring search <term>`; `--family` on `denckring list`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_search.py
from typer.testing import CliRunner

from denckring.cli import app

runner = CliRunner()


def test_search_finds_a_procedure_by_alias() -> None:
    result = runner.invoke(app, ["search", "rhopalic"])
    assert result.exit_code == 0
    assert "snowball" in result.stdout


def test_search_finds_a_procedure_by_id_fragment() -> None:
    assert "lipogram" in runner.invoke(app, ["search", "lipo"]).stdout


def test_search_is_case_insensitive() -> None:
    assert "snowball" in runner.invoke(app, ["search", "RHOPALIC"]).stdout


def test_search_reports_no_match_and_exits_one() -> None:
    result = runner.invoke(app, ["search", "zzzznotathing"])
    assert result.exit_code == 1
    assert "No procedure" in result.stdout


def test_list_filters_by_family() -> None:
    result = runner.invoke(app, ["list", "--family", "letter"])
    assert "lipogram" in result.stdout
    assert "sonnet" not in result.stdout


def test_list_rejects_an_unknown_family() -> None:
    result = runner.invoke(app, ["list", "--family", "nonsense"])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_cli_search.py -v`
Expected: FAIL — no `search` command.

- [ ] **Step 3: Implement**

Add a `--family` option to `list_command`, validated against `FAMILIES`:

```python
    if family and family not in FAMILIES:
        typer.echo(f"Unknown family {family!r}. Known families: {', '.join(FAMILIES)}")
        raise typer.Exit(EXIT_ERROR)
```

and skip rows whose `meta.family` does not match. Then:

```python
@app.command("search")
def search_command(term: str) -> None:
    """Find procedures by id, name or alias. Exits 1 when nothing matches."""
    needle = term.casefold()
    matches: list[str] = []
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        haystack = [procedure_id, *meta.names.values(), *meta.aliases]
        if any(needle in field.casefold() for field in haystack):
            matches.append(procedure_id)
    if not matches:
        typer.echo(f"No procedure matches {term!r}.")
        raise typer.Exit(EXIT_UNSATISFIED)
    for procedure_id in matches:
        meta = catalogue.get(procedure_id)
        alias_note = f"  (also: {', '.join(meta.aliases)})" if meta.aliases else ""
        typer.echo(f"{procedure_id:24} {meta.family:12} {meta.names.get('en', '')}{alias_note}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_cli_search.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: add catalogue search and family filtering"
```

---

### Tasks 3–7: Catalogue expansion, one family group per task

Each of these five tasks follows the identical rhythm:

1. Write the new rows into `src/denckring/data/catalogue.yaml`, grouped under a comment
   banner naming the family.
2. Run `uv run pytest tests/test_catalogue_quality.py` — every row must pass every check.
3. Run `uv run denckring status` and record the new count.
4. Spot-check discovery: `uv run denckring list --family <family>` and
   `uv run denckring search <an alias added in this task>`.
5. Commit.

Row shape, which every new entry follows:

```yaml
  - id: belle_absente
    names: { en: Belle absente, de: Schöne Abwesende, fr: Belle absente }
    definitions:
      en: >-
        A poem in which each line omits exactly one letter of the dedicatee's name,
        taking the letters in order, while using every other letter of the alphabet.
      de: Ein Gedicht, in dem jede Zeile genau einen Buchstaben des Widmungsnamens auslässt.
      fr: Un poème dont chaque vers omet une lettre du nom du dédicataire.
    source: Georges Perec, in Oulipo, Atlas de littérature potentielle (1981)
    family: letter
    attribution: primary
    aliases: [beautiful absent]
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics, alphabet]
    deterministic: true
    prompt_hints:
      en: Write one line per letter of the name, each line omitting that letter and using all the others.
```

German and French names and definitions are written where they are genuine — a form with
no established German name carries only `en`, rather than a translation invented on the
spot. `requires` names capabilities honestly even though nothing implements the row yet;
that is what makes the row a specification rather than a label.

**The attribution rule governs every one of these tasks.** Where the origin is uncertain,
the row says `reference` and names the standard work that documents the form. No row
carries a `primary` attribution with an invented author, work or year.

---

### Task 3: Letter-level forms

**Target:** about 23 new rows, bringing `letter` to roughly 35.

Ground to cover: `belle_absente`, `abecedarian`, `double_acrostic`, `chronogram`,
`semordnilap`, `word_square`, `pangrammatic_window`, `supervocalic`, `consonantal_lipogram`,
`liponym`, `charade`, `kangaroo_word`, `tautonym`, `anagrammatic_verse`, `boustrophedon`,
`acronym_verse`, `alliterative_verse`, `assonance_constraint`, `letter_frequency_constraint`,
`monosyllabic`, `spoonerism`, `heterogram_perfect`, `panvocalic`.

Word Ways forms (`kangaroo_word`, `pangrammatic_window`, `tautonym`, `supervocalic`) take
`attribution: reference` naming Borgmann's *Language on Vacation* (1965) or *Word Ways*
as the journal of record — their individual originators are not reliably established.

- [ ] **Step 1: Write the rows**
- [ ] **Step 2: `uv run pytest tests/test_catalogue_quality.py`** — expected PASS
- [ ] **Step 3: `uv run denckring list --family letter | wc -l`** — expected about 35
- [ ] **Step 4: `uv run pytest && uv run ruff check && uv run mypy --strict src tests`**
- [ ] **Step 5: Commit** — `git commit -m "feat: catalogue letter-level procedures"`

---

### Task 4: Word-level and syntactic forms

**Target:** about 30 new rows across `word` and `syntax`.

Ground to cover: `homoconsonantism`, `homovocalism`, `homosyntaxism`, `perverb`,
`mathews_algorithm`, `chimera`, `canada_dry`, `slenderizing`, `haikuization`,
`lipossible`, `melting_text`, `tmesis`, `epenthesis`, `word_ladder`, `beau_present_word`,
`snowball_sentence`, `sentence_length_constraint`, `single_sentence`, `no_verb`,
`verbless_prose`, `one_syllable_words`, `monosyllabic_prose`, `elementary_deletion`,
`irrational_sonnet_prose`, `antonymic_substitution`, `synonymic_substitution`,
`definitional_expansion`, `larding_variant`, `subject_verb_object_constraint`,
`clause_count_constraint`.

Named Oulipian procedures — `perverb`, `mathews_algorithm`, `chimera`, `canada_dry`,
`haikuization` — carry `primary` with their Oulipian originator where that is
established, and `reference` to the *Oulipo Compendium* where it is not. Do not guess
between Mathews, Roubaud, Jouet and Bénabou; when unsure, use `reference`.

- [ ] **Step 1: Write the rows**
- [ ] **Step 2: `uv run pytest tests/test_catalogue_quality.py`** — expected PASS
- [ ] **Step 3: `uv run denckring status`** — record the count
- [ ] **Step 4: Full verification**
- [ ] **Step 5: Commit** — `git commit -m "feat: catalogue word-level and syntactic procedures"`

---

### Task 5: Form and prosody

**Target:** about 33 new rows, bringing `form` to roughly 40.

Ground to cover: `villanelle`, `sestina`, `quenina`, `pantoum`, `ghazal`, `rondeau`,
`rondel`, `triolet`, `ballade`, `limerick`, `clerihew`, `double_dactyl`, `cinquain`,
`tanka`, `renga`, `haibun`, `senryu`, `ottava_rima`, `rhyme_royal`, `spenserian_stanza`,
`petrarchan_sonnet`, `shakespearean_sonnet`, `curtal_sonnet`, `heroic_couplet`,
`sapphic_stanza`, `alcaic_stanza`, `elegiac_couplet`, `hendecasyllable`, `iambic_pentameter`,
`trochaic_tetrameter`, `dactylic_hexameter`, `englyn`, `cywydd`.

This family is where `traditional` dominates. Use `primary` only where a single named
poet demonstrably established the form — `quenina` (Queneau and Roubaud's generalisation
of the sestina), `clerihew` (E. C. Bentley), `double_dactyl` (Anthony Hecht and Paul
Pascal, 1951), `curtal_sonnet` (Gerard Manley Hopkins). The sestina's attribution to
Arnaut Daniel is conventional rather than documented: use `reference`.

Every row in this family declares `requires: [tokens, syllables]` at minimum, and those
that constrain rhyme add `phonemes`. None is implementable until the syllabification
sub-project, which is exactly what the coverage metric should show.

- [ ] **Step 1: Write the rows**
- [ ] **Step 2: `uv run pytest tests/test_catalogue_quality.py`** — expected PASS
- [ ] **Step 3: `uv run denckring list --family form | wc -l`** — expected about 40
- [ ] **Step 4: Full verification**
- [ ] **Step 5: Commit** — `git commit -m "feat: catalogue prosodic and stanzaic forms"`

---

### Task 6: Permutation and procedural forms

**Target:** about 27 new rows across `permutation` and `procedural`.

Ground to cover — permutation: `cent_mille_milliards`, `combinatorial_sonnet`,
`quenine_generalised`, `permutation_poem`, `tarot_permutation`, `anagrammatic_permutation`,
`line_permutation`, `stanza_permutation`, `word_permutation`.

Procedural: `erasure`, `blackout_poetry`, `cento`, `found_poem`, `collage_text`,
`dada_poem`, `chance_operation`, `aleatory_selection`, `acrostic_reading`,
`every_nth_word`, `column_reading`, `strikethrough`, `overwriting`, `palimpsest`,
`recombination`, `text_folding`, `random_walk_reading`, `oracle_reading`.

Firm attributions here: `cent_mille_milliards` (Queneau, 1961), `erasure` via Tom
Phillips's *A Humument* (1970), `dada_poem` (Tristan Tzara, 1920), `cento` (Ausonius,
4th century — `traditional`), `chance_operation` (John Cage). Where a modern practice has
no single originator — `blackout_poetry`, `found_poem` — use `reference` or `traditional`
rather than crediting a populariser as an inventor.

- [ ] **Step 1: Write the rows**
- [ ] **Step 2: `uv run pytest tests/test_catalogue_quality.py`** — expected PASS
- [ ] **Step 3: `uv run denckring status`** — record the count
- [ ] **Step 4: Full verification**
- [ ] **Step 5: Commit** — `git commit -m "feat: catalogue permutational and procedural forms"`

---

### Task 7: Translation and visual forms, export, and the release files

**Target:** about 20 new rows across `translation` and `visual`, plus the release artifact.

Ground to cover — translation: `homophonic_translation`, `antonymic_translation`,
`definitional_translation`, `lipogrammatic_translation`, `univocalic_translation`,
`transduction`, `intralingual_translation`, `back_translation`, `homomorphic_translation`,
`literal_translation_constraint`.

Visual: `calligram`, `pattern_poem`, `concrete_poetry`, `shaped_verse`, `labyrinth_poem`,
`sator_square`, `typewriter_poem`, `spatial_poem`, `grid_poem`, `visual_acrostic`.

Firm attributions: `homophonic_translation` via Louis Zukofsky's *Catullus* (1969);
`calligram` (Guillaume Apollinaire, *Calligrammes*, 1918); `pattern_poem` (Simmias of
Rhodes, 4th century BC — `reference`); `concrete_poetry` (Eugen Gomringer, 1953);
`sator_square` (`traditional`).

- [ ] **Step 1: Write the rows, then run the quality suite**

Run: `uv run pytest tests/test_catalogue_quality.py`
Expected: PASS.

- [ ] **Step 2: Write the failing export test**

```python
# tests/test_catalogue_export.py
import csv
import io
import json

from typer.testing import CliRunner

from denckring.cli import app
from denckring.core import catalogue

runner = CliRunner()


def test_json_export_contains_every_row() -> None:
    result = runner.invoke(app, ["catalogue", "export", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["procedures"]) == len(catalogue.ids())
    assert payload["licence"].startswith("CC BY 4.0")


def test_json_export_rows_carry_the_new_fields() -> None:
    payload = json.loads(runner.invoke(app, ["catalogue", "export", "--format", "json"]).stdout)
    row = next(r for r in payload["procedures"] if r["id"] == "snowball")
    assert row["family"] == "letter"
    assert row["attribution"]
    assert "rhopalic" in row["aliases"]


def test_csv_export_has_one_line_per_row_plus_a_header() -> None:
    result = runner.invoke(app, ["catalogue", "export", "--format", "csv"])
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert len(rows) == len(catalogue.ids())
    assert rows[0]["id"]


def test_export_writes_to_a_file_when_asked(tmp_path) -> None:
    target = tmp_path / "catalogue.json"
    result = runner.invoke(
        app, ["catalogue", "export", "--format", "json", "--output", str(target)]
    )
    assert result.exit_code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["procedures"]
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/test_catalogue_export.py -v`
Expected: FAIL — no `catalogue` command group.

- [ ] **Step 4: Implement the export**

Add a sub-app to `cli.py`:

```python
catalogue_app = typer.Typer(help="Work with the catalogue as data.")
app.add_typer(catalogue_app, name="catalogue")

CATALOGUE_LICENCE = "CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/"
CATALOGUE_ATTRIBUTION = "denckring catalogue, https://github.com/senzelden/denckring"


@catalogue_app.command("export")
def catalogue_export(
    export_format: Annotated[str, typer.Option("--format")] = "json",
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Emit the catalogue as a standalone dataset."""
    rows = [catalogue.get(pid).model_dump() for pid in catalogue.ids()]
    if export_format == "json":
        text = json.dumps(
            {
                "licence": CATALOGUE_LICENCE,
                "attribution": CATALOGUE_ATTRIBUTION,
                "count": len(rows),
                "procedures": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
    elif export_format == "csv":
        buffer = io.StringIO()
        columns = ["id", "family", "kind", "attribution", "source", "name_en", "definition_en"]
        writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "family": row["family"],
                    "kind": row["kind"],
                    "attribution": row["attribution"],
                    "source": row["source"],
                    "name_en": row["names"].get("en", ""),
                    "definition_en": row["definitions"].get("en", ""),
                }
            )
        text = buffer.getvalue()
    else:
        typer.echo(f"Unknown format {export_format!r}. Use json or csv.")
        raise typer.Exit(EXIT_ERROR)
    if output is None:
        typer.echo(text)
    else:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {output}")
```

Import `csv` and `io` at the top of `cli.py`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_catalogue_export.py -v`
Expected: PASS, 4 tests

- [ ] **Step 6: Write `LICENSE-DATA`**

A CC BY 4.0 notice covering `src/denckring/data/catalogue.yaml` and anything exported
from it: what is licensed, the human-readable summary link, the legal-code link, the
attribution string that satisfies the BY term, and a sentence noting that the code in
this repository is under MIT instead.

- [ ] **Step 7: Update README and CHANGELOG**

README gains a short "The catalogue as data" section: the row count, the export command,
the CC BY licence and the attribution string, and a note that `attribution` distinguishes
a traced origin from a form documented in a standard reference. CHANGELOG gains an
`Added` entry for the schema fields, the search and family commands, the export command
and the expansion, stating the final row count.

- [ ] **Step 8: Full acceptance run**

```bash
uv run pytest
uv run ruff format --check
uv run ruff check
uv run mypy --strict src tests
uv run denckring eval --all
uv run denckring status
uv run denckring search rhopalic
uv run denckring list --family form | head
uv run denckring catalogue export --format json | head -20
uv run denckring catalogue export --format csv | head -3
```

Expected: all green; `status` reporting roughly 150 catalogued, 12 implemented, 12
validated; `search rhopalic` finding `snowball`.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: catalogue translation and visual forms, add dataset export"
```

---

## Self-review notes

Spec coverage: schema fields → Task 1; validation → Task 1; discoverability → Task 2;
expansion to ~150 → Tasks 3–7; export and `LICENSE-DATA` → Task 7. Every acceptance
criterion in the spec has a step that checks it.

The riskiest failure mode is not a bug but a fabricated attribution, which no test can
catch — `test_primary_attributions_name_a_year` only checks that a primary claim cites
*some* year, not that the year is right. The mitigation is the rule stated in the global
constraints and repeated in every data task: when the origin is uncertain, the row is
`reference`. Reviewers should spot-check `primary` rows first, since those are the only
ones asserting an origin.

Names used consistently: `family`, `aliases`, `attribution`, `FAMILIES`, `Family`,
`Attribution`, `catalogue export`, `search`.
