# denckring Skeleton and Batch 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `denckring` package core — protocol, registry, English language pack, eval harness, CLI and scaffolder — plus the twelve lexicon-free restriction procedures of Batch 1.

**Architecture:** Every procedure is a class in its own module under `denckring/procedures/`, discovered by `pkgutil` autodiscovery, whose `Meta` is loaded from a single catalogue YAML. A `BaseProcedure` template method validates language, capability and parameters before delegating to the subclass, so a procedure module cannot forget those checks. Three generic test suites iterate the whole registry, so adding a procedure edits no shared file.

**Tech Stack:** Python 3.11+, uv, hatchling, Pydantic v2, PyYAML, Typer, pytest, Hypothesis, ruff, mypy strict.

## Global Constraints

- Python `>=3.11`. `src/` layout. Build backend hatchling. Managed with `uv` only — never pip, never poetry, never requirements.txt.
- Runtime dependencies are exactly `pydantic>=2.7`, `pyyaml>=6.0`, `typer>=0.12`. Nothing else, ever, in this plan.
- Dev dependencies: `pytest`, `hypothesis`, `mypy`, `ruff`, `types-PyYAML`.
- Type hints everywhere; `uv run mypy --strict src tests` must pass. `uv run ruff check` and `uv run ruff format --check` must pass.
- **The API is English.** No German or French identifiers anywhere in code. German and French live only in catalogue data and language packs.
- **One module per procedure.** No collector modules, no `__init__` that imports procedures by name, no shared per-procedure test file.
- **`check` is mandatory, `apply` optional.** A procedure without a working checker is not registered.
- **No silent fallback.** Any missing language, pack capability or bad parameter raises a `DenckringError` subclass naming exactly what is missing.
- **`satisfied == (score == 1.0)`** for every procedure, always.
- Code licence MIT. Catalogue data CC BY 4.0. Repo URLs point at `https://github.com/senzelden/denckring`.
- No network access at runtime or in tests.
- Every task ends with a commit. Commit messages use Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`).

---

### Task 1: Project scaffold and tooling

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `src/denckring/__init__.py`, `src/denckring/py.typed`, `tests/test_package.py`
- Create: `docs/adr/0001-english-api-multilingual-content.md` … `docs/adr/0008-catalogue-inside-package.md`

**Interfaces:**
- Consumes: nothing.
- Produces: an installed `denckring` package exposing `__version__: str`; the commands `uv run pytest`, `uv run ruff check`, `uv run mypy --strict src tests`.

- [ ] **Step 1: Initialise the project**

```bash
cd /home/claudeuser/denckring
uv init --lib --name denckring --python 3.11 --no-workspace
rm -rf src/denckring/py.typed src/denckring/*.py
uv add "pydantic>=2.7" "pyyaml>=6.0" "typer>=0.12"
uv add --dev pytest hypothesis mypy ruff types-PyYAML
```

If `uv init` refuses because the directory is not empty, create `pyproject.toml` by hand with the content of Step 2 and run only the `uv add` lines.

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "denckring"
version = "0.1.0"
description = "A library of experimental writing procedures, where the validator is the eval"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
license-files = ["LICENSE"]
authors = [{ name = "senzelden", email = "senzelden@gmail.com" }]
keywords = ["oulipo", "constrained-writing", "lipogram", "poetics", "nlp"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Text Processing :: Linguistic",
    "Typing :: Typed",
]
dependencies = ["pydantic>=2.7", "pyyaml>=6.0", "typer>=0.12"]

[project.urls]
Homepage = "https://github.com/senzelden/denckring"
Repository = "https://github.com/senzelden/denckring"
Issues = "https://github.com/senzelden/denckring/issues"

[project.scripts]
denckring = "denckring.cli:app"

[dependency-groups]
dev = ["pytest>=8", "hypothesis>=6.100", "mypy>=1.10", "ruff>=0.5", "types-PyYAML>=6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/denckring"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF", "N", "ANN"]
ignore = ["ANN401"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ANN"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unreachable = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_package.py
import denckring


def test_version_is_exposed():
    assert denckring.__version__ == "0.1.0"
```

- [ ] **Step 4: Run it to verify it fails**

Run: `uv run pytest tests/test_package.py -v`
Expected: FAIL — `AttributeError: module 'denckring' has no attribute '__version__'`

- [ ] **Step 5: Write the minimal implementation**

```python
# src/denckring/__init__.py
"""denckring — a library of experimental writing procedures."""

from importlib.metadata import version

__version__ = version("denckring")

__all__ = ["__version__"]
```

Create an empty `src/denckring/py.typed`.

- [ ] **Step 6: Run it to verify it passes**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS

- [ ] **Step 7: Write `LICENSE`**

The standard MIT licence text, `Copyright (c) 2026 senzelden`.

- [ ] **Step 8: Write the eight ADRs**

Each file follows the same three-heading shape — `## Context`, `## Decision`, `## Consequences` — and is two to six sentences per heading. Titles and decisions:

| File | Decision |
|---|---|
| `0001-english-api-multilingual-content.md` | Identifiers, docstrings and CLI are English; German and French appear only in catalogue data and language packs. A German public API is an adoption barrier for a PyPI package. |
| `0002-check-mandatory-apply-optional.md` | `check` is required for registration; `apply` is optional and only meaningful for `kind` in `{constructive, both}`. The validator is the eval, so a procedure without one has no acceptance criterion. |
| `0003-catalogue-yaml-not-sqlite.md` | The catalogue is a single YAML file read once at import; no SQLite. A few hundred rows do not need a database, and a database would add a build step and a second source of truth. Revisit at >1000 entries or when the docs gallery needs queries. |
| `0004-language-packs-as-capabilities.md` | Packs declare a capability set; a procedure declares `requires`; a mismatch raises `MissingCapability`. Silent approximation across languages is the failure mode that would make the library untrustworthy. |
| `0005-continuous-score.md` | `score` is continuous in `[0, 1]`, monotone in violation count, and `satisfied == (score == 1.0)`. A boolean cannot drive a retry loop. |
| `0006-dual-licence.md` | Code MIT; catalogue data CC BY 4.0 with per-entry source attribution. Copyleft-derived language data must stay behind an extra so core remains permissive. |
| `0007-one-module-per-procedure.md` | Exactly one procedure per module, module name equals procedure id, enforced at registration. Collector modules create merge conflicts between parallel agent runs. |
| `0008-catalogue-inside-package.md` | The catalogue lives at `src/denckring/data/catalogue.yaml`, not the repo-root `data/` the seed sketched, because it must ship in the wheel and be read via `importlib.resources`. The CC BY data release points at that path. |

- [ ] **Step 9: Verify the toolchain is green**

Run: `uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests`
Expected: all four pass. Fix formatting with `uv run ruff format` if the check fails.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: scaffold denckring package with tooling and ADRs"
```

---

### Task 2: Core types and errors

**Files:**
- Create: `src/denckring/core/__init__.py`, `src/denckring/core/protocol.py`, `src/denckring/core/errors.py`
- Test: `tests/test_protocol.py`, `tests/test_errors.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `denckring.core.protocol`: `Lang`, `Kind`, `Violation`, `Report`, `Meta`, `LanguagePack`
  - `denckring.core.errors`: `DenckringError`, `UnknownProcedure(procedure_id)`, `UnknownLanguage(lang)`, `MissingCapability(procedure_id, lang, capability)`, `InvalidParams(procedure_id, message)`, `DuplicateProcedure(procedure_id)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_errors.py
import pytest

from denckring.core.errors import (
    DenckringError,
    InvalidParams,
    MissingCapability,
    UnknownLanguage,
    UnknownProcedure,
)


def test_all_errors_share_a_base():
    for exc in (UnknownProcedure, UnknownLanguage, MissingCapability, InvalidParams):
        assert issubclass(exc, DenckringError)


def test_unknown_language_names_the_extra_to_install():
    err = UnknownLanguage("de")
    assert "de" in str(err)
    assert "denckring[de]" in str(err)


def test_missing_capability_names_procedure_language_and_capability():
    err = MissingCapability("n_plus_7", "en", "lexicon.nouns")
    message = str(err)
    assert "n_plus_7" in message
    assert "en" in message
    assert "lexicon.nouns" in message


def test_unknown_procedure_names_the_id():
    assert "wobble" in str(UnknownProcedure("wobble"))


def test_invalid_params_names_the_procedure():
    err = InvalidParams("lipogram", "forbidden must be a single letter")
    assert "lipogram" in str(err)
    assert "single letter" in str(err)
```

```python
# tests/test_protocol.py
import pytest
from pydantic import ValidationError

from denckring.core.protocol import Meta, Report, Violation


def test_report_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        Report(procedure="lipogram", satisfied=False, score=1.5)


def test_report_defaults_are_empty():
    report = Report(procedure="lipogram", satisfied=True, score=1.0)
    assert report.violations == []
    assert report.metrics == {}


def test_violation_offset_is_optional():
    assert Violation(rule="forbidden_letter", found="e", expected="").offset is None


def test_meta_round_trips_through_json():
    meta = Meta(
        id="lipogram",
        names={"en": "Lipogram"},
        definitions={"en": "A text omitting a chosen letter."},
        source="Georges Perec, La Disparition (1969)",
        kind="restrictive",
        languages=["en"],
        requires=["tokens"],
        deterministic=True,
        prompt_hints={"en": "Write without using the letter e."},
    )
    assert Meta.model_validate(meta.model_dump()) == meta
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_protocol.py tests/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'denckring.core'`

- [ ] **Step 3: Write `errors.py`**

```python
# src/denckring/core/errors.py
"""Every failure mode in denckring is one of these. None of them is silent."""


class DenckringError(Exception):
    """Base class for every error the library raises."""


class UnknownProcedure(DenckringError):
    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(
            f"No procedure with id {procedure_id!r}. "
            f"Run `denckring list` to see the registered procedures."
        )


class UnknownLanguage(DenckringError):
    def __init__(self, lang: str) -> None:
        self.lang = lang
        super().__init__(
            f"No language pack installed for {lang!r}. "
            f"Install it with `pip install denckring[{lang}]`."
        )


class MissingCapability(DenckringError):
    def __init__(self, procedure_id: str, lang: str, capability: str) -> None:
        self.procedure_id = procedure_id
        self.lang = lang
        self.capability = capability
        super().__init__(
            f"Procedure {procedure_id!r} requires the capability {capability!r}, "
            f"which the {lang!r} language pack does not provide."
        )


class InvalidParams(DenckringError):
    def __init__(self, procedure_id: str, message: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(f"Invalid parameters for procedure {procedure_id!r}: {message}")


class DuplicateProcedure(DenckringError):
    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(f"A procedure with id {procedure_id!r} is already registered.")
```

- [ ] **Step 4: Write `protocol.py`**

```python
# src/denckring/core/protocol.py
"""The data contract. Report and Meta serialise to stable JSON for non-Python callers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import ClassVar, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Lang = Literal["en", "de", "fr"]
Kind = Literal["constructive", "restrictive", "both"]


class Violation(BaseModel):
    """One place where a text fails a procedure."""

    rule: str
    offset: int | None = None
    found: str
    expected: str
    note: str | None = None


class Report(BaseModel):
    """The result of checking a text. `satisfied` is always `score == 1.0`."""

    procedure: str
    satisfied: bool
    score: float = Field(ge=0.0, le=1.0)
    violations: list[Violation] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class Meta(BaseModel):
    """A catalogue entry. The single source of truth for a procedure's description."""

    id: str
    names: dict[Lang, str]
    definitions: dict[Lang, str]
    source: str
    kind: Kind
    languages: list[Lang]
    requires: list[str] = Field(default_factory=list)
    deterministic: bool = True
    prompt_hints: dict[Lang, str] = Field(default_factory=dict)


@runtime_checkable
class LanguagePack(Protocol):
    """Per-language behaviour. Methods whose capability is undeclared must raise."""

    lang: ClassVar[Lang]
    capabilities: ClassVar[frozenset[str]]
    word_re: ClassVar[re.Pattern[str]]

    def tokenize(self, text: str) -> list[str]: ...
    def word_spans(self, text: str) -> list[tuple[int, str]]: ...
    def fold_diacritics(self, ch: str) -> str: ...
    def alphabet(self) -> str: ...
    def vowels(self) -> frozenset[str]: ...
    def ascenders(self) -> frozenset[str]: ...
    def descenders(self) -> frozenset[str]: ...
    def syllables(self, word: str) -> list[str]: ...
    def nouns(self) -> Iterable[str]: ...
```

Note for the implementer: the seed sketched `LanguagePack` with four methods and a trailing `...`. `word_spans`, `alphabet`, `vowels`, `ascenders` and `descenders` are additions this plan requires — Batch 1 needs character offsets for `Violation.offset`, and `prisoners_constraint` needs glyph shapes. Create `src/denckring/core/__init__.py` empty.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_protocol.py tests/test_errors.py -v`
Expected: PASS, 8 tests

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add core protocol types and error hierarchy"
```

---

### Task 3: Catalogue loader and initial catalogue

**Files:**
- Create: `src/denckring/core/catalogue.py`, `src/denckring/data/catalogue.yaml`
- Test: `tests/test_catalogue.py`

**Interfaces:**
- Consumes: `Meta` from Task 2.
- Produces:
  - `catalogue.load() -> dict[str, Meta]` (cached)
  - `catalogue.get(procedure_id: str) -> Meta`, raising `UnknownProcedure`
  - `catalogue.ids() -> list[str]` sorted
  - `catalogue.CATALOGUE_PATH: Path`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_catalogue.py
import pytest

from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import Meta


def test_loads_every_row_as_meta():
    entries = catalogue.load()
    assert entries
    assert all(isinstance(m, Meta) for m in entries.values())


def test_row_key_matches_its_id():
    for key, meta in catalogue.load().items():
        assert key == meta.id


def test_get_returns_a_known_entry():
    meta = catalogue.get("lipogram")
    assert meta.kind == "restrictive"
    assert "en" in meta.languages
    assert meta.source


def test_get_raises_on_unknown_id():
    with pytest.raises(UnknownProcedure):
        catalogue.get("wobble")


def test_every_entry_has_an_english_name_definition_and_source():
    for meta in catalogue.load().values():
        assert meta.names.get("en")
        assert meta.definitions.get("en")
        assert meta.source
        assert meta.prompt_hints.get("en")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_catalogue.py -v`
Expected: FAIL — `ImportError: cannot import name 'catalogue'`

- [ ] **Step 3: Write `catalogue.py`**

```python
# src/denckring/core/catalogue.py
"""The catalogue is the single source of truth for procedure metadata."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import Meta

CATALOGUE_PATH = Path(str(files("denckring") / "data" / "catalogue.yaml"))


@lru_cache(maxsize=1)
def load() -> dict[str, Meta]:
    """Read every catalogue row. Cached: the file is read once per process."""
    raw: Any = yaml.safe_load(CATALOGUE_PATH.read_text(encoding="utf-8"))
    entries: dict[str, Meta] = {}
    for row in raw["procedures"]:
        meta = Meta.model_validate(row)
        if meta.id in entries:
            raise ValueError(f"Duplicate catalogue row for {meta.id!r}")
        entries[meta.id] = meta
    return entries


def get(procedure_id: str) -> Meta:
    """Return one entry, or raise `UnknownProcedure`."""
    try:
        return load()[procedure_id]
    except KeyError:
        raise UnknownProcedure(procedure_id) from None


def ids() -> list[str]:
    """Every catalogued id, sorted."""
    return sorted(load())
```

- [ ] **Step 4: Write the catalogue with the twelve Batch 1 rows**

```yaml
# src/denckring/data/catalogue.yaml
# Catalogue of experimental writing procedures.
# Licence: CC BY 4.0. Each row carries its own source attribution.
procedures:
  - id: lipogram
    names: { en: Lipogram, de: Lipogramm, fr: Lipogramme }
    definitions:
      en: A text that omits a chosen letter of the alphabet entirely.
      de: Ein Text, der einen gewählten Buchstaben vollständig auslässt.
      fr: Un texte qui omet entièrement une lettre choisie.
    source: Georges Perec, La Disparition (1969)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a passage that never uses the letter "e", in any case or accented form.

  - id: univocalic
    names: { en: Univocalic, de: Univokalisch, fr: Univocalisme }
    definitions:
      en: A text using only one of the vowels.
      de: Ein Text, der nur einen einzigen Vokal verwendet.
      fr: Un texte n'employant qu'une seule voyelle.
    source: C. C. Bombaugh, Gleanings for the Curious from the Harvest-Fields of Literature (1867)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a passage in which "e" is the only vowel that appears.

  - id: tautogram
    names: { en: Tautogram, de: Tautogramm, fr: Tautogramme }
    definitions:
      en: A text in which every word begins with the same letter.
      de: Ein Text, in dem jedes Wort mit demselben Buchstaben beginnt.
      fr: Un texte dont chaque mot commence par la même lettre.
    source: Hucbald of Saint-Amand, Ecloga de Calvis (c. 890)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a passage in which every single word begins with the letter "p".

  - id: pangram
    names: { en: Pangram, de: Pangramm, fr: Pangramme }
    definitions:
      en: A text containing every letter of the alphabet at least once; a perfect pangram uses each exactly once.
      de: Ein Text, der jeden Buchstaben des Alphabets mindestens einmal enthält.
      fr: Un texte contenant chaque lettre de l'alphabet au moins une fois.
    source: Traditional; catalogued in Oulipo, Atlas de littérature potentielle (1981)
    kind: restrictive
    languages: [en]
    requires: [alphabet, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write one sentence that uses every letter of the alphabet at least once.

  - id: heterogram
    names: { en: Heterogram, de: Heterogramm, fr: Hétérogramme }
    definitions:
      en: A text in which no letter is repeated.
      de: Ein Text, in dem sich kein Buchstabe wiederholt.
      fr: Un texte dans lequel aucune lettre ne se répète.
    source: Dmitri A. Borgmann, Language on Vacation (1965)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a phrase in which no letter of the alphabet appears more than once.

  - id: palindrome
    names: { en: Palindrome, de: Palindrom, fr: Palindrome }
    definitions:
      en: A text that reads identically forwards and backwards, ignoring case, spacing and punctuation.
      de: Ein Text, der vorwärts wie rückwärts gleich lautet.
      fr: Un texte qui se lit identiquement dans les deux sens.
    source: Attributed to Sotades of Maroneia (3rd century BC); revived by Oulipo
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a sentence that reads the same backwards as forwards, letter by letter.

  - id: snowball
    names: { en: Snowball, de: Schneeball, fr: Boule de neige }
    definitions:
      en: A text in which each word is exactly one letter longer than the word before it.
      de: Ein Text, in dem jedes Wort genau einen Buchstaben länger ist als das vorige.
      fr: Un texte dont chaque mot compte une lettre de plus que le précédent.
    source: Ausonius, Technopaegnion (4th century); named in Oulipo, La Littérature potentielle (1973)
    kind: restrictive
    languages: [en]
    requires: [tokens]
    deterministic: true
    prompt_hints:
      en: Write a sentence whose first word has one letter, the next two, the next three, and so on.

  - id: reverse_snowball
    names: { en: Reverse snowball, de: Umgekehrter Schneeball, fr: Boule de neige fondante }
    definitions:
      en: A text in which each word is exactly one letter shorter than the word before it.
      de: Ein Text, in dem jedes Wort genau einen Buchstaben kürzer ist als das vorige.
      fr: Un texte dont chaque mot compte une lettre de moins que le précédent.
    source: Oulipo, La Littérature potentielle (1973), as fonte de neige
    kind: restrictive
    languages: [en]
    requires: [tokens]
    deterministic: true
    prompt_hints:
      en: Write a sentence whose words shrink by exactly one letter each, ending in a single letter.

  - id: prisoners_constraint
    names: { en: Prisoner's constraint, de: Gefangenenbeschränkung, fr: Contrainte du prisonnier }
    definitions:
      en: A text using no letter with an ascender or a descender, as though saving paper.
      de: Ein Text ohne Buchstaben mit Ober- oder Unterlänge.
      fr: Un texte sans lettre à hampe ni à jambage.
    source: Georges Perec, in Oulipo, Atlas de littérature potentielle (1981)
    kind: restrictive
    languages: [en]
    requires: [tokens, letter_shapes, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write using only letters that stay within the x-height — avoid b, d, f, g, h, j, k, l, p, q, t and y.

  - id: beau_present
    names: { en: Beau présent, de: Schönes Geschenk, fr: Beau présent }
    definitions:
      en: A text written using only the letters contained in a dedicatee's name.
      de: Ein Text, der nur die Buchstaben eines Widmungsnamens verwendet.
      fr: Un texte n'employant que les lettres du nom d'un dédicataire.
    source: Georges Perec and Jacques Roubaud, in Oulipo, Atlas de littérature potentielle (1981)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a dedication using only the letters that appear in the dedicatee's name.

  - id: acrostic
    names: { en: Acrostic, de: Akrostichon, fr: Acrostiche }
    definitions:
      en: A text whose initial letters, read down the lines, spell out a target word or phrase.
      de: Ein Text, dessen Anfangsbuchstaben ein Wort ergeben.
      fr: Un texte dont les initiales composent un mot.
    source: Lewis Carroll, A Boat Beneath a Sunny Sky (1871)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a poem whose lines begin with the letters of the target word, in order.

  - id: telestich
    names: { en: Telestich, de: Telestichon, fr: Télestiche }
    definitions:
      en: A text whose final letters, read down the lines, spell out a target word or phrase.
      de: Ein Text, dessen Endbuchstaben ein Wort ergeben.
      fr: Un texte dont les lettres finales composent un mot.
    source: George Puttenham, The Arte of English Poesie (1589)
    kind: restrictive
    languages: [en]
    requires: [tokens, fold_diacritics]
    deterministic: true
    prompt_hints:
      en: Write a poem whose lines end with the letters of the target word, in order.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_catalogue.py -v`
Expected: PASS, 5 tests

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add catalogue loader and the twelve Batch 1 entries"
```

---

### Task 4: Registry with autodiscovery

**Files:**
- Create: `src/denckring/core/registry.py`, `src/denckring/core/base.py`, `src/denckring/procedures/__init__.py`
- Modify: `src/denckring/__init__.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `Meta`, `Report`, `LanguagePack`, errors from Task 2; `catalogue.get` from Task 3.
- Produces:
  - `denckring.core.base.BaseProcedure[P]` with `id: ClassVar[str]`, `meta`, `check(text, *, lang="en", **params) -> Report`, `params_schema() -> dict[str, Any]`, abstract `params_model() -> type[P]` and `_check(text, pack, params) -> Report`, and helper `_report(satisfied_units, total_units, violations, metrics) -> Report`
  - `denckring.core.registry.register(cls)`, `get(procedure_id) -> BaseProcedure[Any]`, `all_procedures() -> dict[str, BaseProcedure[Any]]`
  - Re-exported at top level as `denckring.get`, `denckring.check`, `denckring.list_procedures`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
import pytest

from denckring.core import registry
from denckring.core.base import BaseProcedure
from denckring.core.errors import UnknownProcedure


def test_get_raises_on_unknown_id():
    with pytest.raises(UnknownProcedure):
        registry.get("wobble")


def test_registered_ids_are_a_subset_of_the_catalogue():
    from denckring.core import catalogue

    assert set(registry.all_procedures()) <= set(catalogue.ids())


def test_every_registered_procedure_is_a_base_procedure():
    for proc in registry.all_procedures().values():
        assert isinstance(proc, BaseProcedure)


def test_module_name_must_equal_procedure_id():
    for proc_id, proc in registry.all_procedures().items():
        assert type(proc).__module__.rsplit(".", 1)[-1] == proc_id


def test_registering_a_procedure_whose_module_disagrees_with_its_id_fails():
    from pydantic import BaseModel

    class Params(BaseModel):
        pass

    class Mismatched(BaseProcedure[Params]):
        id = "definitely_not_this_module"

        @classmethod
        def params_model(cls):
            return Params

        def _check(self, text, pack, params):  # pragma: no cover - never reached
            raise NotImplementedError

    with pytest.raises(ValueError, match="module"):
        registry.register(Mismatched)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'denckring.core.registry'`

- [ ] **Step 3: Write `base.py`**

```python
# src/denckring/core/base.py
"""The template method every procedure inherits.

`check` validates language, capability and parameters before delegating, so an
individual procedure module cannot forget those checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from denckring.core import catalogue
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Lang, LanguagePack, Meta, Report, Violation

P = TypeVar("P", bound=BaseModel)


class BaseProcedure(ABC, Generic[P]):
    """A procedure. Subclasses live one per module and are registered by decorator."""

    id: ClassVar[str]

    def __init__(self) -> None:
        self.meta: Meta = catalogue.get(self.id)

    @classmethod
    @abstractmethod
    def params_model(cls) -> type[P]:
        """The Pydantic model describing this procedure's parameters."""

    @abstractmethod
    def _check(self, text: str, pack: LanguagePack, params: P) -> Report:
        """Procedure-specific checking. Language and parameters are already valid."""

    def params_schema(self) -> dict[str, Any]:
        """JSON Schema for the parameters, for non-Python callers."""
        return self.params_model().model_json_schema()

    def check(self, text: str, *, lang: Lang = "en", **params: Any) -> Report:
        """Validate a text against this procedure."""
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in self.meta.requires:
            require_capability(pack, capability, self.id)
        try:
            parsed = self.params_model().model_validate(params)
        except ValidationError as exc:
            raise InvalidParams(self.id, str(exc)) from exc
        return self._check(text, pack, parsed)

    def _report(
        self,
        *,
        good: int,
        total: int,
        violations: list[Violation],
        metrics: dict[str, float],
    ) -> Report:
        """Build a Report enforcing `satisfied == (score == 1.0)`.

        An empty text has `total == 0` and scores 1.0 — vacuously satisfied. A
        procedure for which that is wrong (pangram) must not use this helper.
        """
        score = 1.0 if total == 0 else max(0.0, min(1.0, good / total))
        return Report(
            procedure=self.id,
            satisfied=score == 1.0,
            score=score,
            violations=violations,
            metrics=metrics,
        )


def require_capability(pack: LanguagePack, capability: str, procedure_id: str) -> None:
    """Raise `MissingCapability` unless the pack declares it."""
    from denckring.core.errors import MissingCapability

    if capability not in pack.capabilities:
        raise MissingCapability(procedure_id, pack.lang, capability)
```

- [ ] **Step 4: Write `registry.py`**

```python
# src/denckring/core/registry.py
"""Autodiscovery over `denckring.procedures`. No collector module, by design."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any, TypeVar

from denckring.core.base import BaseProcedure
from denckring.core.errors import DuplicateProcedure, UnknownProcedure

_REGISTRY: dict[str, BaseProcedure[Any]] = {}
_DISCOVERED = False

C = TypeVar("C", bound=type[BaseProcedure[Any]])


def register(cls: C) -> C:
    """Instantiate and register a procedure class. Used as a decorator."""
    procedure_id = cls.id
    module_name = cls.__module__.rsplit(".", 1)[-1]
    if module_name != procedure_id:
        raise ValueError(
            f"Procedure id {procedure_id!r} must equal its module name, got {module_name!r}. "
            f"One module per procedure is enforced — see ADR 0007."
        )
    if procedure_id in _REGISTRY:
        raise DuplicateProcedure(procedure_id)
    _REGISTRY[procedure_id] = cls()
    return cls


def _discover() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    package = importlib.import_module("denckring.procedures")
    for module in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"denckring.procedures.{module.name}")


def all_procedures() -> dict[str, BaseProcedure[Any]]:
    """Every registered procedure, by id."""
    _discover()
    return dict(_REGISTRY)


def get(procedure_id: str) -> BaseProcedure[Any]:
    """One registered procedure, or `UnknownProcedure`."""
    _discover()
    try:
        return _REGISTRY[procedure_id]
    except KeyError:
        raise UnknownProcedure(procedure_id) from None
```

- [ ] **Step 5: Extend the top-level API**

```python
# src/denckring/__init__.py
"""denckring — a library of experimental writing procedures."""

from importlib.metadata import version
from typing import Any

from denckring.core.protocol import Lang, Meta, Report, Violation
from denckring.core.registry import all_procedures, get

__version__ = version("denckring")


def check(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> Report:
    """Check a text against a procedure by id."""
    return get(procedure_id).check(text, lang=lang, **params)


def list_procedures() -> list[str]:
    """Every registered procedure id, sorted."""
    return sorted(all_procedures())


__all__ = [
    "Lang",
    "Meta",
    "Report",
    "Violation",
    "__version__",
    "all_procedures",
    "check",
    "get",
    "list_procedures",
]
```

Create an empty `src/denckring/procedures/__init__.py`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS, 5 tests. `test_registered_ids_are_a_subset_of_the_catalogue` passes vacuously while the registry is empty; it becomes meaningful in Task 6.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add procedure base class and autodiscovering registry"
```

---

### Task 5: Language packs and text helpers

**Files:**
- Create: `src/denckring/lang/__init__.py`, `src/denckring/lang/base.py`, `src/denckring/lang/en.py`, `src/denckring/core/text.py`
- Test: `tests/test_lang_en.py`, `tests/test_text.py`

**Interfaces:**
- Consumes: `LanguagePack`, `Lang`, errors from Task 2.
- Produces:
  - `denckring.lang.base`: capability constants `TOKENS`, `ALPHABET`, `FOLD_DIACRITICS`, `LETTER_SHAPES`, `SYLLABLES`, `NOUNS`; class `BasePack`
  - `denckring.lang.en.EnglishPack`
  - `denckring.lang.get_pack(lang: Lang) -> LanguagePack`
  - `denckring.core.text`: `letter_spans(text, pack) -> list[tuple[int, str]]`, `word_spans(text, pack) -> list[tuple[int, str]]`, `line_spans(text) -> list[tuple[int, str]]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lang_en.py
import pytest

from denckring.core.errors import MissingCapability, UnknownLanguage
from denckring.lang import get_pack
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS


def test_english_pack_declares_the_batch_one_capabilities():
    pack = get_pack("en")
    assert {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES} <= pack.capabilities


def test_unknown_language_raises_with_install_hint():
    with pytest.raises(UnknownLanguage, match=r"denckring\[de\]"):
        get_pack("de")


def test_undeclared_capability_raises_rather_than_approximating():
    pack = get_pack("en")
    with pytest.raises(MissingCapability):
        pack.syllables("potato")
    with pytest.raises(MissingCapability):
        list(pack.nouns())


def test_tokenize_keeps_internal_apostrophes_and_drops_punctuation():
    assert get_pack("en").tokenize("Don't stop, Anna!") == ["Don't", "stop", "Anna"]


def test_fold_diacritics_maps_accented_letters_to_bare_ones():
    pack = get_pack("en")
    assert pack.fold_diacritics("é") == "e"
    assert pack.fold_diacritics("E") == "e"
    assert pack.fold_diacritics("ß") == "ss"


def test_letter_shapes_cover_the_prisoner_constraint_set():
    pack = get_pack("en")
    assert pack.ascenders() | pack.descenders() == set("bdfghjklpqty")
```

```python
# tests/test_text.py
from denckring.core.text import letter_spans, line_spans, word_spans
from denckring.lang import get_pack

PACK = get_pack("en")


def test_letter_spans_fold_and_lowercase_and_carry_offsets():
    assert letter_spans("Éh!", PACK) == [(0, "e"), (1, "h")]


def test_letter_spans_ignore_digits_and_punctuation():
    assert letter_spans("a1 b.", PACK) == [(0, "a"), (3, "b")]


def test_word_spans_carry_offsets():
    assert word_spans("one two", PACK) == [(0, "one"), (4, "two")]


def test_line_spans_skip_blank_lines_and_carry_offsets():
    assert line_spans("a\n\n b \n") == [(0, "a"), (3, " b ")]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_lang_en.py tests/test_text.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'denckring.lang'`

- [ ] **Step 3: Write `lang/base.py`**

```python
# src/denckring/lang/base.py
"""Capability constants and the shared pack implementation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import ClassVar

from denckring.core.errors import MissingCapability
from denckring.core.protocol import Lang

TOKENS = "tokens"
ALPHABET = "alphabet"
FOLD_DIACRITICS = "fold_diacritics"
LETTER_SHAPES = "letter_shapes"
SYLLABLES = "syllables"
NOUNS = "lexicon.nouns"

WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


class BasePack:
    """Shared behaviour. A method whose capability is undeclared must raise."""

    lang: ClassVar[Lang]
    capabilities: ClassVar[frozenset[str]] = frozenset()
    word_re: ClassVar[re.Pattern[str]] = WORD_RE

    def _require(self, capability: str) -> None:
        if capability not in self.capabilities:
            raise MissingCapability("<caller>", self.lang, capability)

    def tokenize(self, text: str) -> list[str]:
        return [word for _, word in self.word_spans(text)]

    def word_spans(self, text: str) -> list[tuple[int, str]]:
        return [(m.start(), m.group()) for m in self.word_re.finditer(text)]

    def fold_diacritics(self, ch: str) -> str:
        """Lower-case and strip combining marks. Returns "" for non-letters."""
        lowered = ch.lower()
        decomposed = unicodedata.normalize("NFKD", lowered)
        folded = "".join(c for c in decomposed if not unicodedata.combining(c))
        return folded

    def alphabet(self) -> str:
        raise MissingCapability("<caller>", self.lang, ALPHABET)

    def vowels(self) -> frozenset[str]:
        raise MissingCapability("<caller>", self.lang, ALPHABET)

    def ascenders(self) -> frozenset[str]:
        raise MissingCapability("<caller>", self.lang, LETTER_SHAPES)

    def descenders(self) -> frozenset[str]:
        raise MissingCapability("<caller>", self.lang, LETTER_SHAPES)

    def syllables(self, word: str) -> list[str]:
        raise MissingCapability("<caller>", self.lang, SYLLABLES)

    def nouns(self) -> Iterable[str]:
        raise MissingCapability("<caller>", self.lang, NOUNS)
```

`ß` folds to `ss` under NFKD, which is what `test_fold_diacritics_maps_accented_letters_to_bare_ones` expects. Callers of `fold_diacritics` must therefore handle a multi-character return.

- [ ] **Step 4: Write `lang/en.py` and `lang/__init__.py`**

```python
# src/denckring/lang/en.py
"""English. Ships in core with no data files and no heavy dependencies."""

from __future__ import annotations

from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS, BasePack

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VOWELS = frozenset("aeiou")
_ASCENDERS = frozenset("bdfhklt")
_DESCENDERS = frozenset("fgjpqy")


class EnglishPack(BasePack):
    lang: ClassVar[Lang] = "en"
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

```python
# src/denckring/lang/__init__.py
"""Language pack lookup. Third-party packs register via the entry point group."""

from __future__ import annotations

from denckring.core.errors import UnknownLanguage
from denckring.core.protocol import Lang, LanguagePack
from denckring.lang.en import EnglishPack

_PACKS: dict[str, LanguagePack] = {"en": EnglishPack()}


def get_pack(lang: Lang | str) -> LanguagePack:
    """Return the installed pack for a language, or raise `UnknownLanguage`."""
    try:
        return _PACKS[lang]
    except KeyError:
        raise UnknownLanguage(str(lang)) from None


def register_pack(pack: LanguagePack) -> None:
    """Install a pack. Used by the `de` and `fr` extras and by third parties."""
    _PACKS[pack.lang] = pack


__all__ = ["get_pack", "register_pack"]
```

- [ ] **Step 5: Write `core/text.py`**

```python
# src/denckring/core/text.py
"""Offset-preserving text helpers. Violations need character offsets."""

from __future__ import annotations

from denckring.core.protocol import LanguagePack


def letter_spans(text: str, pack: LanguagePack) -> list[tuple[int, str]]:
    """Every alphabetic character as `(offset, folded lowercase letter)`."""
    spans: list[tuple[int, str]] = []
    for offset, ch in enumerate(text):
        if not ch.isalpha():
            continue
        folded = pack.fold_diacritics(ch)
        spans.extend((offset, letter) for letter in folded if letter.isalpha())
    return spans


def word_spans(text: str, pack: LanguagePack) -> list[tuple[int, str]]:
    """Every word as `(offset, word)`, unfolded."""
    return pack.word_spans(text)


def line_spans(text: str) -> list[tuple[int, str]]:
    """Every non-blank line as `(offset, line)`, keeping the original text."""
    spans: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if stripped.strip():
            spans.append((offset, stripped))
        offset += len(line)
    return spans
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lang_en.py tests/test_text.py -v`
Expected: PASS, 10 tests

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add language pack interface, English pack and text helpers"
```

---

### Task 6: The lipogram vertical slice and the three generic suites

This is the task that proves the contract before it is copied eleven times. Nothing after it invents structure.

**Files:**
- Create: `src/denckring/procedures/lipogram.py`, `src/denckring/eval/__init__.py`, `src/denckring/eval/fixtures/golden/lipogram.yaml`
- Create: `tests/strategies/__init__.py`, `tests/strategies/lipogram.py`, `tests/conftest.py`, `tests/test_golden.py`, `tests/test_strategies.py`, `tests/test_invariants.py`, `tests/test_lipogram.py`

**Interfaces:**
- Consumes: `BaseProcedure`, `register`, `letter_spans`, `get_pack`.
- Produces:
  - `denckring.procedures.lipogram.Lipogram` with `LipogramParams(forbidden: str = "e")`
  - Golden fixture format: a YAML mapping with keys `procedure`, `lang`, `cases`, each case having `name`, `text`, `params`, `satisfied`, and optional `source` and `min_score`/`max_score`
  - `tests/strategies/<id>.py` module contract: `satisfying(draw_params) -> SearchStrategy[tuple[str, dict]]` and `violating(...) -> SearchStrategy[tuple[str, dict]]`, both yielding `(text, params)` pairs
  - `tests/conftest.py`: fixtures `all_procs`, `golden_cases`

- [ ] **Step 1: Write the failing per-procedure test**

```python
# tests/test_lipogram.py
import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_text_without_the_letter_is_satisfied():
    report = check("lipogram", "This is a small conforming bit of writing.", forbidden="z")
    assert report.satisfied
    assert report.score == 1.0
    assert report.violations == []


def test_default_forbidden_letter_is_e():
    assert not check("lipogram", "Here is an example.").satisfied


def test_violations_carry_offsets():
    report = check("lipogram", "abc e", forbidden="e")
    assert [v.offset for v in report.violations] == [4]
    assert report.violations[0].rule == "forbidden_letter"


def test_accented_forms_count_as_the_bare_letter():
    assert not check("lipogram", "café", forbidden="e").satisfied


def test_score_falls_as_violations_rise():
    few = check("lipogram", "aaaaaaaaae", forbidden="e").score
    many = check("lipogram", "aaaaaeeeee", forbidden="e").score
    assert few > many


def test_empty_text_is_vacuously_satisfied():
    assert check("lipogram", "").satisfied


def test_bad_parameter_raises_invalid_params():
    with pytest.raises(InvalidParams):
        check("lipogram", "text", forbidden="ee")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_lipogram.py -v`
Expected: FAIL — `UnknownProcedure: No procedure with id 'lipogram'`

- [ ] **Step 3: Write the procedure**

```python
# src/denckring/procedures/lipogram.py
"""Lipogram — a text omitting a chosen letter."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class LipogramParams(BaseModel):
    forbidden: str = Field(default="e", description="The letter the text must omit.")

    @field_validator("forbidden")
    @classmethod
    def _single_letter(cls, value: str) -> str:
        if len(value) != 1 or not value.isalpha():
            raise ValueError("forbidden must be a single alphabetic character")
        return value.lower()


@register
class Lipogram(BaseProcedure[LipogramParams]):
    id = "lipogram"

    @classmethod
    def params_model(cls) -> type[LipogramParams]:
        return LipogramParams

    def _check(self, text: str, pack: LanguagePack, params: LipogramParams) -> Report:
        letters = letter_spans(text, pack)
        violations = [
            Violation(
                rule="forbidden_letter",
                offset=offset,
                found=letter,
                expected=f"any letter but {params.forbidden!r}",
            )
            for offset, letter in letters
            if letter == params.forbidden
        ]
        return self._report(
            good=len(letters) - len(violations),
            total=len(letters),
            violations=violations,
            metrics={"letters": float(len(letters)), "hits": float(len(violations))},
        )
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_lipogram.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Write the golden fixture**

```yaml
# src/denckring/eval/fixtures/golden/lipogram.yaml
procedure: lipogram
lang: en
cases:
  - name: gadsby-opening
    source: Ernest Vincent Wright, Gadsby (1939)
    text: >-
      If youth, throughout all history, had had a champion to stand up for it;
      to show a doubting world that a child can think.
    params: { forbidden: e }
    satisfied: true
  - name: ordinary-prose
    source: constructed counterexample
    text: The letter appears here repeatedly.
    params: { forbidden: e }
    satisfied: false
    max_score: 0.95
```

- [ ] **Step 6: Write the Hypothesis strategies**

```python
# tests/strategies/lipogram.py
"""Generators for lipogram. `satisfying` and `violating` are the module contract."""

from hypothesis import strategies as st

_LETTERS = "abcdfghijklmnopqrstuvwxyz"  # deliberately without "e"


def satisfying():
    return st.text(alphabet=_LETTERS + " ", min_size=0, max_size=60).map(
        lambda text: (text, {"forbidden": "e"})
    )


def violating():
    return st.tuples(
        st.text(alphabet=_LETTERS + " ", max_size=30),
        st.text(alphabet=_LETTERS + " ", max_size=30),
    ).map(lambda parts: (parts[0] + "e" + parts[1], {"forbidden": "e"}))
```

Create an empty `tests/strategies/__init__.py`.

- [ ] **Step 7: Write `conftest.py`**

```python
# tests/conftest.py
"""Fixtures shared by the three registry-wide suites."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from denckring.core.registry import all_procedures

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "src/denckring/eval/fixtures/golden"
STRATEGY_DIR = Path(__file__).resolve().parent / "strategies"


@dataclass(frozen=True)
class GoldenCase:
    procedure: str
    lang: str
    name: str
    text: str
    params: dict[str, Any]
    satisfied: bool
    min_score: float | None
    max_score: float | None

    def __str__(self) -> str:
        return f"{self.procedure}:{self.name}"


def load_golden_cases() -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    for path in sorted(GOLDEN_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            cases.append(
                GoldenCase(
                    procedure=data["procedure"],
                    lang=data.get("lang", "en"),
                    name=case["name"],
                    text=case["text"],
                    params=case.get("params", {}),
                    satisfied=case["satisfied"],
                    min_score=case.get("min_score"),
                    max_score=case.get("max_score"),
                )
            )
    return cases


def strategy_module(procedure_id: str):
    return importlib.import_module(f"strategies.{procedure_id}")


def pytest_generate_tests(metafunc):
    if "procedure_id" in metafunc.fixturenames:
        ids = sorted(all_procedures())
        metafunc.parametrize("procedure_id", ids, ids=ids)
    if "golden_case" in metafunc.fixturenames:
        cases = load_golden_cases()
        metafunc.parametrize("golden_case", cases, ids=[str(c) for c in cases])
```

Add `pythonpath = ["tests"]` to `[tool.pytest.ini_options]` in `pyproject.toml` so `strategies.<id>` imports resolve.

- [ ] **Step 8: Write the three generic suites**

```python
# tests/test_golden.py
"""Level 1: every golden example must check exactly as recorded."""

from denckring import check


def test_golden_case(golden_case):
    report = check(
        golden_case.procedure, golden_case.text, lang=golden_case.lang, **golden_case.params
    )
    assert report.satisfied is golden_case.satisfied
    if golden_case.min_score is not None:
        assert report.score >= golden_case.min_score
    if golden_case.max_score is not None:
        assert report.score <= golden_case.max_score


def test_every_registered_procedure_has_a_golden_file(procedure_id):
    from conftest import GOLDEN_DIR

    assert (GOLDEN_DIR / f"{procedure_id}.yaml").exists()


def test_every_procedure_has_a_positive_and_a_negative_case(procedure_id):
    from conftest import load_golden_cases

    cases = [c for c in load_golden_cases() if c.procedure == procedure_id]
    assert any(c.satisfied for c in cases)
    assert any(not c.satisfied for c in cases)
```

```python
# tests/test_strategies.py
"""Level 2: generated texts must agree with the checker, both ways."""

from hypothesis import HealthCheck, given, settings

from denckring import check
from conftest import strategy_module

SETTINGS = settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def test_satisfying_texts_check_true(procedure_id):
    module = strategy_module(procedure_id)

    @SETTINGS
    @given(module.satisfying())
    def run(case):
        text, params = case
        report = check(procedure_id, text, **params)
        assert report.satisfied, f"{text!r} with {params} should satisfy {procedure_id}"
        assert report.score == 1.0

    run()


def test_violating_texts_check_false(procedure_id):
    module = strategy_module(procedure_id)

    @SETTINGS
    @given(module.violating())
    def run(case):
        text, params = case
        report = check(procedure_id, text, **params)
        assert not report.satisfied, f"{text!r} with {params} should violate {procedure_id}"
        assert report.violations

    run()
```

```python
# tests/test_invariants.py
"""Universal invariants. Every registered procedure, no exceptions."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from denckring.core.errors import DenckringError
from denckring.core.registry import all_procedures, get
from denckring.lang import get_pack

SETTINGS = settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def test_meta_id_matches_registry_key(procedure_id):
    assert get(procedure_id).meta.id == procedure_id


def test_module_name_matches_id(procedure_id):
    assert type(get(procedure_id)).__module__.rsplit(".", 1)[-1] == procedure_id


def test_required_capabilities_exist_in_every_declared_pack(procedure_id):
    proc = get(procedure_id)
    for lang in proc.meta.languages:
        pack = get_pack(lang)
        missing = set(proc.meta.requires) - set(pack.capabilities)
        assert not missing, f"{procedure_id} requires {missing} unsupported by {lang}"


def test_params_schema_is_json_serialisable(procedure_id):
    import json

    json.dumps(get(procedure_id).params_schema())


def test_check_is_deterministic_and_well_formed(procedure_id):
    proc = get(procedure_id)

    @SETTINGS
    @given(st.text(max_size=120))
    def run(text):
        try:
            first = proc.check(text)
            second = proc.check(text)
        except DenckringError:
            return  # a required parameter is missing; covered by the per-procedure tests
        assert first == second
        assert 0.0 <= first.score <= 1.0
        assert first.satisfied == (first.score == 1.0)
        assert first.procedure == procedure_id

    run()


def test_check_raises_nothing_but_denckring_error(procedure_id):
    proc = get(procedure_id)

    @SETTINGS
    @given(st.text(max_size=120))
    def run(text):
        try:
            proc.check(text)
        except DenckringError:
            pass

    run()


def test_registry_is_not_empty():
    assert all_procedures()
```

- [ ] **Step 9: Run everything and verify it is green**

Run: `uv run pytest -v`
Expected: PASS. If `test_check_is_deterministic_and_well_formed` reports a required-parameter failure, that is the signal a procedure needs a default — Batch 1 procedures with required params (`beau_present`, `acrostic`, `telestich`) are handled in their own tasks by catching `DenckringError`, as written above.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: add lipogram and the three registry-wide test suites"
```

---

### Task 7: Eval harness

**Files:**
- Create: `src/denckring/eval/harness.py`
- Test: `tests/test_harness.py`

**Interfaces:**
- Consumes: registry, catalogue, golden fixtures.
- Produces:
  - `harness.golden_cases() -> list[GoldenCase]` (a Pydantic model with the same fields as the test dataclass)
  - `harness.run() -> Scoreboard` where `Scoreboard` has `rows: list[ProcedureResult]`, `passed: int`, `failed: int`, `catalogued: int`, `implemented: int`, `validated: int`, and `ok: bool`
  - `harness.status() -> Coverage` with `catalogued`, `implemented`, `validated`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_harness.py
from denckring.eval import harness


def test_run_is_green_on_the_shipped_fixtures():
    board = harness.run()
    assert board.failed == 0
    assert board.ok
    assert board.passed == len(harness.golden_cases())


def test_status_counts_are_consistent():
    coverage = harness.status()
    assert coverage.catalogued >= coverage.implemented >= coverage.validated
    assert coverage.implemented == len(harness.implemented_ids())


def test_scoreboard_serialises_to_json():
    harness.run().model_dump_json()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_harness.py -v`
Expected: FAIL — `ImportError: cannot import name 'harness'`

- [ ] **Step 3: Write `harness.py`**

```python
# src/denckring/eval/harness.py
"""Level 3: the scoreboard. This is the CI gate and the unattended-run criterion."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from denckring.core import catalogue
from denckring.core.errors import DenckringError
from denckring.core.registry import all_procedures, get

GOLDEN_DIR = Path(str(files("denckring") / "eval" / "fixtures" / "golden"))


class GoldenCase(BaseModel):
    procedure: str
    lang: str = "en"
    name: str
    text: str
    params: dict[str, Any] = Field(default_factory=dict)
    satisfied: bool
    source: str | None = None
    min_score: float | None = None
    max_score: float | None = None


class CaseResult(BaseModel):
    case: str
    procedure: str
    lang: str
    passed: bool
    detail: str | None = None


class Coverage(BaseModel):
    catalogued: int
    implemented: int
    validated: int

    def line(self) -> str:
        return (
            f"{self.catalogued} catalogued · "
            f"{self.implemented} implemented · "
            f"{self.validated} validated"
        )


class Scoreboard(BaseModel):
    results: list[CaseResult]
    coverage: Coverage

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def golden_cases() -> list[GoldenCase]:
    """Every shipped golden example, across every procedure."""
    cases: list[GoldenCase] = []
    for path in sorted(GOLDEN_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for row in data["cases"]:
            cases.append(
                GoldenCase(procedure=data["procedure"], lang=data.get("lang", "en"), **row)
            )
    return cases


def implemented_ids() -> list[str]:
    return sorted(all_procedures())


def validated_ids() -> list[str]:
    with_fixtures = {c.procedure for c in golden_cases()}
    return sorted(with_fixtures & set(implemented_ids()))


def status() -> Coverage:
    """The project metric."""
    return Coverage(
        catalogued=len(catalogue.ids()),
        implemented=len(implemented_ids()),
        validated=len(validated_ids()),
    )


def run() -> Scoreboard:
    """Run every golden case through its procedure."""
    results: list[CaseResult] = []
    for case in golden_cases():
        detail: str | None = None
        try:
            report = get(case.procedure).check(case.text, lang=case.lang, **case.params)
            passed = report.satisfied is case.satisfied
            if passed and case.min_score is not None:
                passed = report.score >= case.min_score
            if passed and case.max_score is not None:
                passed = report.score <= case.max_score
            if not passed:
                detail = f"satisfied={report.satisfied} score={report.score:.3f}"
        except DenckringError as exc:
            passed = False
            detail = str(exc)
        results.append(
            CaseResult(
                case=case.name,
                procedure=case.procedure,
                lang=case.lang,
                passed=passed,
                detail=detail,
            )
        )
    return Scoreboard(results=results, coverage=status())
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_harness.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add eval harness with scoreboard and coverage metric"
```

---

### Task 8: CLI

**Files:**
- Create: `src/denckring/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: registry, catalogue, harness.
- Produces: the `denckring` console script with subcommands `check`, `apply`, `list`, `show`, `status`, `eval`. (`new` arrives in Task 9.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import json

from typer.testing import CliRunner

from denckring.cli import app

runner = CliRunner()


def test_list_prints_registered_ids():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "lipogram" in result.stdout


def test_check_exits_zero_when_satisfied(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("a small conforming bit of writing", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--param", "forbidden=z"])
    assert result.exit_code == 0


def test_check_exits_one_when_unsatisfied(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("here is the letter", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path)])
    assert result.exit_code == 1


def test_check_json_emits_a_valid_report(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("here is the letter", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["procedure"] == "lipogram"
    assert payload["satisfied"] is False


def test_check_reads_stdin():
    result = runner.invoke(app, ["check", "lipogram", "-"], input="aaa")
    assert result.exit_code == 0


def test_status_prints_the_coverage_line():
    result = runner.invoke(app, ["status"])
    assert "catalogued" in result.stdout
    assert "validated" in result.stdout


def test_eval_all_is_green():
    result = runner.invoke(app, ["eval", "--all"])
    assert result.exit_code == 0


def test_show_includes_source_and_params_schema():
    result = runner.invoke(app, ["show", "lipogram", "--json"])
    payload = json.loads(result.stdout)
    assert payload["meta"]["source"]
    assert "forbidden" in payload["params_schema"]["properties"]


def test_apply_on_a_restrictive_procedure_fails_informatively(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["apply", "lipogram", str(path)])
    assert result.exit_code == 2
    assert "restrictive" in result.stdout


def test_unknown_language_is_reported_not_traced(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--lang", "de"])
    assert result.exit_code == 2
    assert "denckring[de]" in result.stdout
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'denckring.cli'`

- [ ] **Step 3: Write `cli.py`**

```python
# src/denckring/cli.py
"""The command line. `check` exits 1 when unsatisfied, so it composes in pipelines."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from denckring.core import catalogue
from denckring.core.errors import DenckringError
from denckring.core.registry import all_procedures, get
from denckring.eval import harness

app = typer.Typer(add_completion=False, help="Experimental writing procedures.")

EXIT_UNSATISFIED = 1
EXIT_ERROR = 2


def _read(source: str | None) -> str:
    if source is None or source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _parse_params(pairs: list[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        if not _:
            raise typer.BadParameter(f"--param expects key=value, got {pair!r}")
        params[key] = _coerce(value)
    return params


def _coerce(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _fail(exc: DenckringError) -> None:
    typer.echo(str(exc))
    raise typer.Exit(EXIT_ERROR)


@app.command("check")
def check_command(
    procedure_id: str,
    file: Annotated[str | None, typer.Argument(help="Path, or - for stdin")] = None,
    lang: str = "en",
    param: Annotated[list[str] | None, typer.Option("--param", "-p")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Validate a text. Exits 1 when the text does not satisfy the procedure."""
    try:
        report = get(procedure_id).check(_read(file), lang=lang, **_parse_params(param or []))
    except DenckringError as exc:
        _fail(exc)
        return
    if as_json:
        typer.echo(report.model_dump_json(indent=2))
    else:
        mark = "satisfied" if report.satisfied else "not satisfied"
        typer.echo(f"{procedure_id}: {mark} (score {report.score:.3f})")
        for violation in report.violations[:20]:
            where = "" if violation.offset is None else f" at {violation.offset}"
            typer.echo(f"  {violation.rule}{where}: found {violation.found!r}")
        if len(report.violations) > 20:
            typer.echo(f"  … and {len(report.violations) - 20} more")
    if not report.satisfied:
        raise typer.Exit(EXIT_UNSATISFIED)


@app.command("apply")
def apply_command(
    procedure_id: str,
    file: Annotated[str | None, typer.Argument(help="Path, or - for stdin")] = None,
    lang: str = "en",
    seed: int | None = None,
    param: Annotated[list[str] | None, typer.Option("--param", "-p")] = None,
) -> None:
    """Generate text with a procedure, where the procedure supports it."""
    try:
        procedure = get(procedure_id)
    except DenckringError as exc:
        _fail(exc)
        return
    generate = getattr(procedure, "apply", None)
    if generate is None:
        typer.echo(
            f"Procedure {procedure_id!r} is {procedure.meta.kind} and has no apply(). "
            f"Only constructive procedures can generate text."
        )
        raise typer.Exit(EXIT_ERROR)
    try:
        typer.echo(
            generate(_read(file), lang=lang, seed=seed, **_parse_params(param or []))
        )
    except DenckringError as exc:
        _fail(exc)


@app.command("list")
def list_command(
    lang: str | None = None,
    kind: str | None = None,
    status: Annotated[str | None, typer.Option(help="catalogued|implemented|validated")] = None,
) -> None:
    """List catalogue entries."""
    implemented = set(harness.implemented_ids())
    validated = set(harness.validated_ids())
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        entry_status = (
            "validated"
            if procedure_id in validated
            else "implemented"
            if procedure_id in implemented
            else "catalogued"
        )
        if lang and lang not in meta.languages:
            continue
        if kind and meta.kind != kind:
            continue
        if status and entry_status != status:
            continue
        typer.echo(f"{procedure_id:24} {entry_status:12} {meta.names.get('en', '')}")


@app.command("show")
def show_command(procedure_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Show a procedure's metadata, parameters and golden examples."""
    try:
        meta = catalogue.get(procedure_id)
    except DenckringError as exc:
        _fail(exc)
        return
    examples = [c.model_dump() for c in harness.golden_cases() if c.procedure == procedure_id]
    schema: dict[str, Any] = {}
    if procedure_id in all_procedures():
        schema = get(procedure_id).params_schema()
    if as_json:
        typer.echo(
            json.dumps(
                {"meta": meta.model_dump(), "params_schema": schema, "examples": examples},
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    typer.echo(f"{meta.names.get('en', procedure_id)} ({meta.id})")
    typer.echo(f"  {meta.definitions.get('en', '')}")
    typer.echo(f"  source: {meta.source}")
    typer.echo(f"  kind: {meta.kind}   languages: {', '.join(meta.languages)}")
    typer.echo(f"  requires: {', '.join(meta.requires) or '—'}")
    for example in examples:
        typer.echo(f"  example [{example['name']}] satisfied={example['satisfied']}")


@app.command("status")
def status_command(as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Print catalogue coverage — the project metric."""
    coverage = harness.status()
    typer.echo(coverage.model_dump_json(indent=2) if as_json else coverage.line())


@app.command("eval")
def eval_command(
    run_all: Annotated[bool, typer.Option("--all")] = True,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run every golden example. Exits non-zero on regression."""
    board = harness.run()
    if as_json:
        typer.echo(board.model_dump_json(indent=2))
    else:
        for result in board.results:
            mark = "ok  " if result.passed else "FAIL"
            typer.echo(f"{mark} {result.procedure:24} {result.case}"
                       + (f"  — {result.detail}" if result.detail else ""))
        typer.echo(
            f"{len(set(r.procedure for r in board.results))} procedures · "
            f"{board.passed} passed · {board.failed} failed"
        )
        typer.echo(board.coverage.line())
    if not board.ok:
        raise typer.Exit(EXIT_UNSATISFIED)
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Verify by hand and show the output**

Run: `uv run denckring list && uv run denckring status && uv run denckring eval --all`
Expected: a list containing `lipogram`, a coverage line, and a green eval.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add typer CLI with check, apply, list, show, status and eval"
```

---

### Task 9: Scaffolder — `denckring new`

**Files:**
- Create: `src/denckring/scaffold/__init__.py`, `src/denckring/scaffold/generator.py`, `src/denckring/scaffold/templates/procedure.py.tmpl`, `templates/test.py.tmpl`, `templates/strategy.py.tmpl`, `templates/golden.yaml.tmpl`, `templates/catalogue_row.yaml.tmpl`
- Modify: `src/denckring/cli.py` (add the `new` command)
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: nothing from the registry — the scaffolder writes files only.
- Produces: `scaffold.generator.scaffold(procedure_id: str, root: Path) -> list[Path]`, and the `denckring new <id>` command.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scaffold.py
import pytest

from denckring.scaffold.generator import class_name, scaffold


def test_class_name_is_pascal_case():
    assert class_name("reverse_snowball") == "ReverseSnowball"
    assert class_name("n_plus_7") == "NPlus7"


def test_scaffold_writes_five_files(tmp_path):
    (tmp_path / "src/denckring/procedures").mkdir(parents=True)
    (tmp_path / "src/denckring/eval/fixtures/golden").mkdir(parents=True)
    (tmp_path / "tests/strategies").mkdir(parents=True)
    (tmp_path / "src/denckring/data").mkdir(parents=True)
    (tmp_path / "src/denckring/data/catalogue.yaml").write_text("procedures:\n", encoding="utf-8")

    written = scaffold("demo_thing", tmp_path)

    assert len(written) == 5
    module = (tmp_path / "src/denckring/procedures/demo_thing.py").read_text(encoding="utf-8")
    assert "class DemoThing(BaseProcedure[DemoThingParams])" in module
    assert 'id = "demo_thing"' in module
    assert "raise NotImplementedError" in module


def test_scaffold_refuses_to_overwrite(tmp_path):
    (tmp_path / "src/denckring/procedures").mkdir(parents=True)
    (tmp_path / "src/denckring/procedures/demo_thing.py").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        scaffold("demo_thing", tmp_path)


def test_scaffold_appends_a_catalogue_row(tmp_path):
    (tmp_path / "src/denckring/procedures").mkdir(parents=True)
    (tmp_path / "src/denckring/eval/fixtures/golden").mkdir(parents=True)
    (tmp_path / "tests/strategies").mkdir(parents=True)
    (tmp_path / "src/denckring/data").mkdir(parents=True)
    (tmp_path / "src/denckring/data/catalogue.yaml").write_text("procedures:\n", encoding="utf-8")

    scaffold("demo_thing", tmp_path)

    catalogue_text = (tmp_path / "src/denckring/data/catalogue.yaml").read_text(encoding="utf-8")
    assert "id: demo_thing" in catalogue_text
    assert "FILL IN" in catalogue_text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'denckring.scaffold'`

- [ ] **Step 3: Write the templates**

`src/denckring/scaffold/templates/procedure.py.tmpl` — `$id` and `$class` are `string.Template` placeholders:

```python
"""$class — FILL IN a one-line description."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register


class ${class}Params(BaseModel):
    pass


@register
class $class(BaseProcedure[${class}Params]):
    id = "$id"

    @classmethod
    def params_model(cls) -> type[${class}Params]:
        return ${class}Params

    def _check(self, text: str, pack: LanguagePack, params: ${class}Params) -> Report:
        raise NotImplementedError("FILL IN the checker for $id")
```

`templates/test.py.tmpl`:

```python
from denckring import check


def test_$id_accepts_a_conforming_text():
    raise AssertionError("FILL IN a conforming example for $id")


def test_$id_rejects_a_violating_text():
    raise AssertionError("FILL IN a violating example for $id")
```

`templates/strategy.py.tmpl`:

```python
"""Generators for $id. Both must yield (text, params) pairs."""

from hypothesis import strategies as st


def satisfying():
    raise NotImplementedError("FILL IN a strategy producing texts that satisfy $id")


def violating():
    raise NotImplementedError("FILL IN a strategy producing texts that violate $id")
```

`templates/golden.yaml.tmpl`:

```yaml
procedure: $id
lang: en
cases:
  - name: FILL-IN-authentic-example
    source: FILL IN a real literary source
    text: FILL IN
    params: {}
    satisfied: true
  - name: FILL-IN-counterexample
    source: constructed counterexample
    text: FILL IN
    params: {}
    satisfied: false
```

`templates/catalogue_row.yaml.tmpl`:

```yaml

  - id: $id
    names: { en: FILL IN }
    definitions:
      en: FILL IN one sentence.
    source: FILL IN author, work (year)
    kind: restrictive
    languages: [en]
    requires: [tokens]
    deterministic: true
    prompt_hints:
      en: FILL IN an instruction a model could follow.
```

- [ ] **Step 4: Write `generator.py` and wire up the CLI**

```python
# src/denckring/scaffold/generator.py
"""Deterministic scaffolding. An agent fills in logic and invents no structure."""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from string import Template

TEMPLATES = Path(str(files("denckring") / "scaffold" / "templates"))


def class_name(procedure_id: str) -> str:
    """`reverse_snowball` -> `ReverseSnowball`, `n_plus_7` -> `NPlus7`."""
    return "".join(part.capitalize() for part in re.split(r"[_\-]", procedure_id))


def _render(template: str, procedure_id: str) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    return Template(text).substitute(id=procedure_id, **{"class": class_name(procedure_id)})


def scaffold(procedure_id: str, root: Path) -> list[Path]:
    """Write module, test, strategy, golden fixture and catalogue row. Never overwrites."""
    targets = {
        "procedure.py.tmpl": root / f"src/denckring/procedures/{procedure_id}.py",
        "test.py.tmpl": root / f"tests/test_{procedure_id}.py",
        "strategy.py.tmpl": root / f"tests/strategies/{procedure_id}.py",
        "golden.yaml.tmpl": root / f"src/denckring/eval/fixtures/golden/{procedure_id}.yaml",
    }
    for path in targets.values():
        if path.exists():
            raise FileExistsError(f"{path} already exists — refusing to overwrite")

    written: list[Path] = []
    for template, path in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(template, procedure_id), encoding="utf-8")
        written.append(path)

    catalogue_path = root / "src/denckring/data/catalogue.yaml"
    with catalogue_path.open("a", encoding="utf-8") as handle:
        handle.write(_render("catalogue_row.yaml.tmpl", procedure_id))
    written.append(catalogue_path)
    return written
```

Add to `cli.py`:

```python
@app.command("new")
def new_command(procedure_id: str, root: Path = Path(".")) -> None:
    """Scaffold a new procedure: module, test, strategy, fixture and catalogue row."""
    from denckring.scaffold.generator import scaffold

    try:
        for path in scaffold(procedure_id, root):
            typer.echo(f"wrote {path}")
    except FileExistsError as exc:
        typer.echo(str(exc))
        raise typer.Exit(EXIT_ERROR) from exc
    typer.echo(f"Now fill in the FILL IN markers, starting with {procedure_id}.py")
```

Create an empty `src/denckring/scaffold/__init__.py`. Add to `pyproject.toml` under `[tool.hatch.build.targets.wheel]`:

```toml
[tool.hatch.build]
artifacts = ["src/denckring/scaffold/templates/*.tmpl"]
```

- [ ] **Step 5: Run it to verify it passes**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: PASS, 4 tests

- [ ] **Step 6: Prove the scaffolder fails informatively rather than vacuously**

```bash
cd /tmp && rm -rf scaffold-probe && mkdir scaffold-probe && cd scaffold-probe
mkdir -p src/denckring/procedures src/denckring/eval/fixtures/golden tests/strategies src/denckring/data
printf 'procedures:\n' > src/denckring/data/catalogue.yaml
cd /home/claudeuser/denckring && uv run denckring new demo_probe --root /tmp/scaffold-probe
grep -c "FILL IN" /tmp/scaffold-probe/src/denckring/procedures/demo_probe.py
rm -rf /tmp/scaffold-probe
```

Expected: five `wrote …` lines and a non-zero `FILL IN` count.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add denckring new scaffolder with deterministic templates"
```

---

### Tasks 10–14: the remaining eleven procedures

Each of these five tasks follows the identical five-step rhythm, and each procedure is generated with `uv run denckring new <id>` first so no structure is invented:

1. `uv run denckring new <id>` (then replace the scaffolded catalogue row with the real one from Task 3's catalogue, which already contains every Batch 1 entry — delete the appended `FILL IN` row).
2. Write the per-procedure test and the golden fixture; run them and watch them fail.
3. Write `_check`; run until green.
4. Write the Hypothesis strategies; run `uv run pytest tests/test_strategies.py -k <id>`.
5. `uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests`, then commit.

Because Task 3 already wrote all twelve catalogue rows, step 1's appended row is a duplicate and must be deleted — `catalogue.load()` raises `ValueError: Duplicate catalogue row` if it is not, which is the intended guard.

---

### Task 10: univocalic, tautogram, pangram

**Files:**
- Create: `src/denckring/procedures/{univocalic,tautogram,pangram}.py`
- Create: `src/denckring/eval/fixtures/golden/{univocalic,tautogram,pangram}.yaml`
- Create: `tests/strategies/{univocalic,tautogram,pangram}.py`, `tests/test_{univocalic,tautogram,pangram}.py`

**Interfaces:**
- Consumes: `BaseProcedure`, `register`, `letter_spans`, `word_spans`, `pack.vowels()`, `pack.alphabet()`.
- Produces: `UnivocalicParams(vowel: str | None = None)`, `TautogramParams(initial: str | None = None)`, `PangramParams(perfect: bool = False)`.

- [ ] **Step 1: Scaffold all three**

```bash
uv run denckring new univocalic && uv run denckring new tautogram && uv run denckring new pangram
```

Then delete the three appended `FILL IN` rows from `src/denckring/data/catalogue.yaml` — the real rows are already there from Task 3.

- [ ] **Step 2: Write the per-procedure tests**

```python
# tests/test_univocalic.py
from denckring import check


def test_single_vowel_text_is_satisfied():
    assert check("univocalic", "Persever, ye perfect men, ever keep these precepts ten").satisfied


def test_mixed_vowels_are_not_satisfied():
    assert not check("univocalic", "the cat sat").satisfied


def test_explicit_vowel_parameter_is_respected():
    assert check("univocalic", "a lad", vowel="a").satisfied
    assert not check("univocalic", "a lad", vowel="o").satisfied


def test_vowel_is_inferred_from_the_majority_when_unset():
    report = check("univocalic", "peer deed")
    assert report.satisfied
    assert report.metrics["vowel_count"] == 4.0


def test_empty_text_is_vacuously_satisfied():
    assert check("univocalic", "").satisfied
```

```python
# tests/test_tautogram.py
from denckring import check


def test_every_word_sharing_an_initial_is_satisfied():
    assert check("tautogram", "Peter Piper picked a peck", initial="p").satisfied is False
    assert check("tautogram", "Peter Piper picked pickled peppers", initial="p").satisfied


def test_initial_is_inferred_from_the_first_word():
    assert check("tautogram", "silent seas sing softly").satisfied


def test_violations_point_at_the_offending_word():
    report = check("tautogram", "pale pink moon", initial="p")
    assert report.violations[0].found == "moon"
    assert report.violations[0].offset == 11


def test_accented_initials_fold():
    assert check("tautogram", "élan easy east", initial="e").satisfied


def test_empty_text_is_vacuously_satisfied():
    assert check("tautogram", "").satisfied
```

```python
# tests/test_pangram.py
from denckring import check


def test_classic_pangram_is_satisfied():
    assert check("pangram", "The quick brown fox jumps over the lazy dog.").satisfied


def test_missing_letters_are_reported_and_scored():
    report = check("pangram", "abc")
    assert not report.satisfied
    assert report.score == 3 / 26
    assert {v.expected for v in report.violations} >= {"z"}


def test_perfect_pangram_requires_each_letter_exactly_once():
    perfect = "Mr Jock, TV quiz PhD, bags few lynx"
    assert check("pangram", perfect, perfect=True).satisfied
    assert not check("pangram", "The quick brown fox jumps over the lazy dog.", perfect=True).satisfied


def test_empty_text_scores_zero():
    report = check("pangram", "")
    assert not report.satisfied
    assert report.score == 0.0
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_univocalic.py tests/test_tautogram.py tests/test_pangram.py -v`
Expected: FAIL — `NotImplementedError` from the scaffolded `_check`.

- [ ] **Step 4: Write the three checkers**

```python
# src/denckring/procedures/univocalic.py
"""Univocalic — a text using only one of the vowels."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class UnivocalicParams(BaseModel):
    vowel: str | None = Field(default=None, description="The permitted vowel; inferred if unset.")

    @field_validator("vowel")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("vowel must be a single alphabetic character")
        return value.lower()


@register
class Univocalic(BaseProcedure[UnivocalicParams]):
    id = "univocalic"

    @classmethod
    def params_model(cls) -> type[UnivocalicParams]:
        return UnivocalicParams

    def _check(self, text: str, pack: LanguagePack, params: UnivocalicParams) -> Report:
        vowel_set = pack.vowels()
        found = [(offset, ch) for offset, ch in letter_spans(text, pack) if ch in vowel_set]
        permitted = params.vowel
        if permitted is None and found:
            permitted = Counter(ch for _, ch in found).most_common(1)[0][0]
        violations = [
            Violation(
                rule="foreign_vowel",
                offset=offset,
                found=ch,
                expected=permitted or "",
            )
            for offset, ch in found
            if ch != permitted
        ]
        return self._report(
            good=len(found) - len(violations),
            total=len(found),
            violations=violations,
            metrics={"vowel_count": float(len(found)), "foreign": float(len(violations))},
        )
```

```python
# src/denckring/procedures/tautogram.py
"""Tautogram — every word begins with the same letter."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class TautogramParams(BaseModel):
    initial: str | None = Field(default=None, description="Shared initial; inferred if unset.")

    @field_validator("initial")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("initial must be a single alphabetic character")
        return value.lower()


@register
class Tautogram(BaseProcedure[TautogramParams]):
    id = "tautogram"

    @classmethod
    def params_model(cls) -> type[TautogramParams]:
        return TautogramParams

    def _check(self, text: str, pack: LanguagePack, params: TautogramParams) -> Report:
        words = word_spans(text, pack)
        initials = [(offset, word, pack.fold_diacritics(word[0])[:1]) for offset, word in words]
        expected = params.initial
        if expected is None and initials:
            expected = initials[0][2]
        violations = [
            Violation(rule="wrong_initial", offset=offset, found=word, expected=expected or "")
            for offset, word, initial in initials
            if initial != expected
        ]
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "wrong": float(len(violations))},
        )
```

```python
# src/denckring/procedures/pangram.py
"""Pangram — the text contains every letter of the alphabet."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class PangramParams(BaseModel):
    perfect: bool = Field(default=False, description="Require each letter exactly once.")


@register
class Pangram(BaseProcedure[PangramParams]):
    id = "pangram"

    @classmethod
    def params_model(cls) -> type[PangramParams]:
        return PangramParams

    def _check(self, text: str, pack: LanguagePack, params: PangramParams) -> Report:
        alphabet = pack.alphabet()
        counts = Counter(ch for _, ch in letter_spans(text, pack) if ch in alphabet)
        missing = [ch for ch in alphabet if ch not in counts]
        violations = [
            Violation(rule="missing_letter", offset=None, found="", expected=ch) for ch in missing
        ]
        coverage = (len(alphabet) - len(missing)) / len(alphabet)
        score = coverage
        if params.perfect:
            excess = sum(count - 1 for count in counts.values() if count > 1)
            violations += [
                Violation(rule="repeated_letter", offset=None, found=ch, expected=f"{ch} once")
                for ch, count in sorted(counts.items())
                if count > 1
            ]
            score = coverage * len(alphabet) / (len(alphabet) + excess)
        return Report(
            procedure=self.id,
            satisfied=score == 1.0,
            score=score,
            violations=violations,
            metrics={
                "coverage": coverage,
                "distinct_letters": float(len(counts)),
                "total_letters": float(sum(counts.values())),
            },
        )
```

`pangram` is the one procedure that must not use `_report`: an empty text is unsatisfied at score 0.0, not vacuously satisfied.

- [ ] **Step 5: Run them to verify they pass**

Run: `uv run pytest tests/test_univocalic.py tests/test_tautogram.py tests/test_pangram.py -v`
Expected: PASS

- [ ] **Step 6: Write the golden fixtures**

```yaml
# src/denckring/eval/fixtures/golden/univocalic.yaml
procedure: univocalic
lang: en
cases:
  - name: bombaugh-e-univocalic
    source: C. C. Bombaugh, Gleanings for the Curious (1867)
    text: Persever, ye perfect men, ever keep these precepts ten.
    params: { vowel: e }
    satisfied: true
  - name: ordinary-prose
    source: constructed counterexample
    text: The cat sat on the mat.
    params: { vowel: e }
    satisfied: false
```

```yaml
# src/denckring/eval/fixtures/golden/tautogram.yaml
procedure: tautogram
lang: en
cases:
  - name: peter-piper
    source: Traditional English tongue-twister, first printed 1813
    text: Peter Piper picked pickled peppers
    params: { initial: p }
    satisfied: true
  - name: broken-run
    source: constructed counterexample
    text: Peter Piper picked a peck
    params: { initial: p }
    satisfied: false
```

```yaml
# src/denckring/eval/fixtures/golden/pangram.yaml
procedure: pangram
lang: en
cases:
  - name: quick-brown-fox
    source: Traditional typing exercise, in use by 1885
    text: The quick brown fox jumps over the lazy dog.
    params: {}
    satisfied: true
  - name: perfect-pangram
    source: Traditional perfect pangram
    text: Mr Jock, TV quiz PhD, bags few lynx
    params: { perfect: true }
    satisfied: true
  - name: not-a-pangram
    source: constructed counterexample
    text: The quick brown fox.
    params: {}
    satisfied: false
```

- [ ] **Step 7: Write the strategies**

```python
# tests/strategies/univocalic.py
from hypothesis import strategies as st

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def satisfying():
    return st.tuples(
        st.sampled_from("aeiou"), st.text(alphabet=_CONSONANTS + " ", min_size=1, max_size=40)
    ).map(lambda pair: (pair[1] + pair[0] + pair[1], {"vowel": pair[0]}))


def violating():
    return st.text(alphabet=_CONSONANTS + " ", max_size=30).map(
        lambda body: (f"a{body}o", {"vowel": "a"})
    )
```

```python
# tests/strategies/tautogram.py
from hypothesis import strategies as st

_TAIL = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=0, max_size=6)


def satisfying():
    return st.tuples(st.sampled_from("abcdefghijklmnopqrstuvwxyz"), st.lists(_TAIL, max_size=6)).map(
        lambda pair: (" ".join(pair[0] + tail for tail in pair[1]), {"initial": pair[0]})
    )


def violating():
    return st.lists(_TAIL, min_size=1, max_size=5).map(
        lambda tails: (" ".join(["p" + t for t in tails] + ["zebra"]), {"initial": "p"})
    )
```

```python
# tests/strategies/pangram.py
from hypothesis import strategies as st

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def satisfying():
    return st.text(alphabet=_ALPHABET + " ", max_size=20).map(
        lambda extra: (_ALPHABET + " " + extra, {})
    )


def violating():
    return st.sampled_from(_ALPHABET).map(
        lambda dropped: (_ALPHABET.replace(dropped, ""), {})
    )
```

- [ ] **Step 8: Verify everything and commit**

Run: `uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests && uv run denckring eval --all`
Expected: all green, four procedures in the scoreboard.

```bash
git add -A
git commit -m "feat: add univocalic, tautogram and pangram procedures"
```

---

### Task 11: heterogram and palindrome

**Files:**
- Create: `src/denckring/procedures/{heterogram,palindrome}.py`, matching golden fixtures, strategies and tests.

**Interfaces:**
- Consumes: `letter_spans`, `word_spans`.
- Produces: `HeterogramParams(scope: Literal["text", "word"] = "text")`, `PalindromeParams(unit: Literal["letter", "word"] = "letter")`.

- [ ] **Step 1: Scaffold, then delete the duplicate catalogue rows**

```bash
uv run denckring new heterogram && uv run denckring new palindrome
```

- [ ] **Step 2: Write the tests**

```python
# tests/test_heterogram.py
from denckring import check


def test_text_with_no_repeated_letter_is_satisfied():
    assert check("heterogram", "Mr Jock, TV quiz PhD, bags few lynx").satisfied


def test_repeats_are_violations_with_offsets():
    report = check("heterogram", "abca")
    assert not report.satisfied
    assert report.violations[0].offset == 3


def test_word_scope_allows_repeats_across_words():
    assert check("heterogram", "cat dog", scope="word").satisfied
    assert not check("heterogram", "cat dog", scope="text").satisfied


def test_empty_text_is_vacuously_satisfied():
    assert check("heterogram", "").satisfied
```

```python
# tests/test_palindrome.py
from denckring import check


def test_classic_palindrome_is_satisfied():
    assert check("palindrome", "A man, a plan, a canal: Panama").satisfied


def test_non_palindrome_is_not_satisfied():
    assert not check("palindrome", "not a palindrome at all").satisfied


def test_word_unit_compares_whole_words():
    assert check("palindrome", "you can cage a swallow can't you", unit="word").satisfied is False
    assert check("palindrome", "bird sings bird", unit="word").satisfied


def test_score_reflects_how_close_the_text_is():
    assert 0.0 < check("palindrome", "abcdba").score < 1.0


def test_empty_text_is_vacuously_satisfied():
    assert check("palindrome", "").satisfied
```

- [ ] **Step 3: Run to verify they fail** — `uv run pytest tests/test_heterogram.py tests/test_palindrome.py -v`, expect `NotImplementedError`.

- [ ] **Step 4: Write the checkers**

```python
# src/denckring/procedures/heterogram.py
"""Heterogram — no letter repeats."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class HeterogramParams(BaseModel):
    scope: Literal["text", "word"] = Field(default="text", description="Where repeats are banned.")


@register
class Heterogram(BaseProcedure[HeterogramParams]):
    id = "heterogram"

    @classmethod
    def params_model(cls) -> type[HeterogramParams]:
        return HeterogramParams

    def _check(self, text: str, pack: LanguagePack, params: HeterogramParams) -> Report:
        groups: list[list[tuple[int, str]]]
        if params.scope == "text":
            groups = [letter_spans(text, pack)]
        else:
            groups = [
                [(offset + i, ch) for i, (_, ch) in enumerate(letter_spans(word, pack))]
                for offset, word in word_spans(text, pack)
            ]
        violations: list[Violation] = []
        total = 0
        for group in groups:
            seen: set[str] = set()
            for offset, ch in group:
                total += 1
                if ch in seen:
                    violations.append(
                        Violation(
                            rule="repeated_letter",
                            offset=offset,
                            found=ch,
                            expected="an unused letter",
                        )
                    )
                seen.add(ch)
        return self._report(
            good=total - len(violations),
            total=total,
            violations=violations,
            metrics={"letters": float(total), "repeats": float(len(violations))},
        )
```

```python
# src/denckring/procedures/palindrome.py
"""Palindrome — the text reads identically in both directions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class PalindromeParams(BaseModel):
    unit: Literal["letter", "word"] = Field(default="letter", description="What is mirrored.")


@register
class Palindrome(BaseProcedure[PalindromeParams]):
    id = "palindrome"

    @classmethod
    def params_model(cls) -> type[PalindromeParams]:
        return PalindromeParams

    def _check(self, text: str, pack: LanguagePack, params: PalindromeParams) -> Report:
        if params.unit == "letter":
            spans = letter_spans(text, pack)
        else:
            spans = [
                (offset, "".join(ch for _, ch in letter_spans(word, pack)))
                for offset, word in word_spans(text, pack)
            ]
        values = [value for _, value in spans]
        mirrored = list(reversed(values))
        violations = [
            Violation(
                rule="mirror_mismatch",
                offset=spans[i][0],
                found=values[i],
                expected=mirrored[i],
            )
            for i in range(len(values))
            if values[i] != mirrored[i]
        ]
        return self._report(
            good=len(values) - len(violations),
            total=len(values),
            violations=violations,
            metrics={"units": float(len(values)), "mismatches": float(len(violations))},
        )
```

- [ ] **Step 5: Run to verify they pass** — `uv run pytest tests/test_heterogram.py tests/test_palindrome.py -v`

- [ ] **Step 6: Write the golden fixtures**

```yaml
# src/denckring/eval/fixtures/golden/heterogram.yaml
procedure: heterogram
lang: en
cases:
  - name: perfect-heterogram
    source: Traditional perfect pangram, also a heterogram
    text: Mr Jock, TV quiz PhD, bags few lynx
    params: {}
    satisfied: true
  - name: ordinary-prose
    source: constructed counterexample
    text: letters repeat here
    params: {}
    satisfied: false
```

```yaml
# src/denckring/eval/fixtures/golden/palindrome.yaml
procedure: palindrome
lang: en
cases:
  - name: mercer-panama
    source: Leigh Mercer, in Notes and Queries (1948)
    text: "A man, a plan, a canal: Panama"
    params: {}
    satisfied: true
  - name: ordinary-prose
    source: constructed counterexample
    text: this sentence does not mirror
    params: {}
    satisfied: false
```

- [ ] **Step 7: Write the strategies**

```python
# tests/strategies/heterogram.py
from hypothesis import strategies as st

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def satisfying():
    return st.lists(st.sampled_from(_ALPHABET), unique=True, max_size=26).map(
        lambda letters: ("".join(letters), {})
    )


def violating():
    return st.tuples(st.sampled_from(_ALPHABET), st.text(alphabet=" ", max_size=3)).map(
        lambda pair: (pair[0] + pair[1] + pair[0], {})
    )
```

```python
# tests/strategies/palindrome.py
from hypothesis import strategies as st

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def satisfying():
    return st.tuples(
        st.text(alphabet=_ALPHABET, max_size=12), st.sampled_from(["", "x"])
    ).map(lambda pair: (pair[0] + pair[1] + pair[0][::-1], {}))


def violating():
    return st.text(alphabet=_ALPHABET, min_size=1, max_size=12).map(
        lambda body: ("a" + body + "b", {})
    )
```

- [ ] **Step 8: Verify and commit**

Run: `uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests`

```bash
git add -A
git commit -m "feat: add heterogram and palindrome procedures"
```

---

### Task 12: snowball and reverse_snowball

**Files:**
- Create: `src/denckring/procedures/{snowball,reverse_snowball}.py`, matching fixtures, strategies and tests.

**Interfaces:**
- Consumes: `word_spans`.
- Produces: `SnowballParams(start: int | None = None, step: int = 1)`; `ReverseSnowball` subclasses `Snowball` with `step` defaulting to `-1` via `ReverseSnowballParams`.

- [ ] **Step 1: Scaffold both, delete the duplicate catalogue rows**

- [ ] **Step 2: Write the tests**

```python
# tests/test_snowball.py
from denckring import check


def test_borgmann_rhopalic_is_satisfied():
    text = "I do not know where family doctors acquired illegibly perplexing handwriting"
    assert check("snowball", text).satisfied


def test_a_wrong_length_word_is_a_violation():
    report = check("snowball", "I do nope know")
    assert not report.satisfied
    assert report.violations[0].found == "nope"
    assert report.violations[0].expected == "3 letters"


def test_start_length_can_be_forced():
    assert check("snowball", "ab abc abcd", start=2).satisfied
    assert not check("snowball", "ab abc abcd", start=1).satisfied


def test_single_word_is_satisfied():
    assert check("snowball", "word").satisfied


def test_empty_text_is_vacuously_satisfied():
    assert check("snowball", "").satisfied
```

```python
# tests/test_reverse_snowball.py
from denckring import check


def test_shrinking_words_are_satisfied():
    text = "handwriting perplexing illegibly acquired doctors family where know not do I"
    assert check("reverse_snowball", text).satisfied


def test_growing_words_are_not_satisfied():
    assert not check("reverse_snowball", "I do not").satisfied
```

- [ ] **Step 3: Run to verify they fail.**

- [ ] **Step 4: Write the checkers**

```python
# src/denckring/procedures/snowball.py
"""Snowball — each word is one letter longer than the last."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class SnowballParams(BaseModel):
    start: int | None = Field(default=None, description="Length of the first word; inferred if unset.")
    step: int = Field(default=1, description="Letters added per word; negative to shrink.")


@register
class Snowball(BaseProcedure[SnowballParams]):
    id = "snowball"

    @classmethod
    def params_model(cls) -> type[SnowballParams]:
        return SnowballParams

    def _check(self, text: str, pack: LanguagePack, params: SnowballParams) -> Report:
        words = word_spans(text, pack)
        if not words:
            return self._report(good=0, total=0, violations=[], metrics={"words": 0.0})
        start = params.start if params.start is not None else len(words[0][1])
        violations: list[Violation] = []
        for index, (offset, word) in enumerate(words):
            expected = start + index * params.step
            if len(word) != expected:
                violations.append(
                    Violation(
                        rule="wrong_word_length",
                        offset=offset,
                        found=word,
                        expected=f"{expected} letters",
                    )
                )
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "wrong": float(len(violations))},
        )
```

```python
# src/denckring/procedures/reverse_snowball.py
"""Reverse snowball — each word is one letter shorter than the last."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.registry import register
from denckring.procedures.snowball import Snowball


class ReverseSnowballParams(BaseModel):
    start: int | None = Field(default=None, description="Length of the first word; inferred if unset.")
    step: int = Field(default=-1, description="Letters removed per word.")


@register
class ReverseSnowball(Snowball):
    id = "reverse_snowball"

    @classmethod
    def params_model(cls) -> type[ReverseSnowballParams]:  # type: ignore[override]
        return ReverseSnowballParams
```

If mypy objects to the `params_model` override, change `Snowball` to `class Snowball(BaseProcedure[SnowballParams])` and `ReverseSnowball` to inherit `BaseProcedure[ReverseSnowballParams]` directly, copying the seven-line `_check` body rather than fighting the variance. Duplication of seven lines is cheaper than an ignore comment; delete the `type: ignore` either way.

- [ ] **Step 5: Run to verify they pass.**

- [ ] **Step 6: Write the fixtures**

```yaml
# src/denckring/eval/fixtures/golden/snowball.yaml
procedure: snowball
lang: en
cases:
  - name: borgmann-rhopalic
    source: Dmitri A. Borgmann, Language on Vacation (1965)
    text: I do not know where family doctors acquired illegibly perplexing handwriting
    params: {}
    satisfied: true
  - name: ordinary-prose
    source: constructed counterexample
    text: the words here do not grow
    params: {}
    satisfied: false
```

```yaml
# src/denckring/eval/fixtures/golden/reverse_snowball.yaml
procedure: reverse_snowball
lang: en
cases:
  - name: borgmann-rhopalic-reversed
    source: Dmitri A. Borgmann, Language on Vacation (1965), read backwards
    text: handwriting perplexing illegibly acquired doctors family where know not do I
    params: {}
    satisfied: true
  - name: growing-instead
    source: constructed counterexample
    text: I do not know
    params: {}
    satisfied: false
```

- [ ] **Step 7: Write the strategies**

```python
# tests/strategies/snowball.py
from hypothesis import strategies as st


def _word(length):
    return st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=length, max_size=length)


def satisfying():
    return st.integers(min_value=1, max_value=6).flatmap(
        lambda count: st.tuples(*[_word(i + 1) for i in range(count)])
    ).map(lambda words: (" ".join(words), {}))


def violating():
    return st.tuples(_word(1), _word(2), _word(2)).map(lambda w: (" ".join(w), {}))
```

```python
# tests/strategies/reverse_snowball.py
from hypothesis import strategies as st


def _word(length):
    return st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=length, max_size=length)


def satisfying():
    return st.integers(min_value=1, max_value=6).flatmap(
        lambda count: st.tuples(*[_word(count - i) for i in range(count)])
    ).map(lambda words: (" ".join(words), {}))


def violating():
    return st.tuples(_word(3), _word(3), _word(1)).map(lambda w: (" ".join(w), {}))
```

- [ ] **Step 8: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A
git commit -m "feat: add snowball and reverse snowball procedures"
```

---

### Task 13: prisoners_constraint and beau_present

**Files:**
- Create: `src/denckring/procedures/{prisoners_constraint,beau_present}.py`, matching fixtures, strategies and tests.

**Interfaces:**
- Consumes: `letter_spans`, `pack.ascenders()`, `pack.descenders()`.
- Produces: `PrisonersConstraintParams()` (no fields); `BeauPresentParams(name: str, require_all: bool = False)`.

- [ ] **Step 1: Scaffold both, delete the duplicate catalogue rows.**

- [ ] **Step 2: Write the tests**

```python
# tests/test_prisoners_constraint.py
import pytest

from denckring import check
from denckring.core.errors import MissingCapability


def test_text_without_ascenders_or_descenders_is_satisfied():
    assert check("prisoners_constraint", "no one can see us or an oar").satisfied


def test_an_ascender_is_a_violation():
    report = check("prisoners_constraint", "a lone man")
    assert not report.satisfied
    assert report.violations[0].found == "l"


def test_a_descender_is_a_violation():
    assert not check("prisoners_constraint", "a page").satisfied


def test_capability_is_declared_in_the_catalogue():
    from denckring.core import catalogue

    assert "letter_shapes" in catalogue.get("prisoners_constraint").requires


def test_empty_text_is_vacuously_satisfied():
    assert check("prisoners_constraint", "").satisfied
```

```python
# tests/test_beau_present.py
import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_text_within_the_name_letters_is_satisfied():
    assert check("beau_present", "a rare cameo", name="Marcel Camoe").satisfied


def test_a_foreign_letter_is_a_violation():
    report = check("beau_present", "a zebra", name="Marcel")
    assert not report.satisfied
    assert {v.found for v in report.violations} == {"z", "b"}


def test_require_all_demands_every_name_letter_be_used():
    assert check("beau_present", "arc", name="arc").satisfied
    assert not check("beau_present", "arc", name="arch", require_all=True).satisfied


def test_missing_name_is_an_invalid_params_error():
    with pytest.raises(InvalidParams):
        check("beau_present", "text")
```

- [ ] **Step 3: Run to verify they fail.**

- [ ] **Step 4: Write the checkers**

```python
# src/denckring/procedures/prisoners_constraint.py
"""Prisoner's constraint — no letter with an ascender or a descender."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class PrisonersConstraintParams(BaseModel):
    pass


@register
class PrisonersConstraint(BaseProcedure[PrisonersConstraintParams]):
    id = "prisoners_constraint"

    @classmethod
    def params_model(cls) -> type[PrisonersConstraintParams]:
        return PrisonersConstraintParams

    def _check(
        self, text: str, pack: LanguagePack, params: PrisonersConstraintParams
    ) -> Report:
        forbidden = pack.ascenders() | pack.descenders()
        letters = letter_spans(text, pack)
        violations = [
            Violation(
                rule="tall_or_deep_letter",
                offset=offset,
                found=ch,
                expected="a letter within the x-height",
            )
            for offset, ch in letters
            if ch in forbidden
        ]
        return self._report(
            good=len(letters) - len(violations),
            total=len(letters),
            violations=violations,
            metrics={"letters": float(len(letters)), "forbidden": float(len(violations))},
        )
```

```python
# src/denckring/procedures/beau_present.py
"""Beau présent — a text using only the letters of a dedicatee's name."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class BeauPresentParams(BaseModel):
    name: str = Field(description="The dedicatee's name, whose letters are the alphabet.")
    require_all: bool = Field(default=False, description="Every name letter must appear.")


@register
class BeauPresent(BaseProcedure[BeauPresentParams]):
    id = "beau_present"

    @classmethod
    def params_model(cls) -> type[BeauPresentParams]:
        return BeauPresentParams

    def _check(self, text: str, pack: LanguagePack, params: BeauPresentParams) -> Report:
        allowed = {ch for _, ch in letter_spans(params.name, pack)}
        letters = letter_spans(text, pack)
        violations = [
            Violation(
                rule="letter_outside_name",
                offset=offset,
                found=ch,
                expected="".join(sorted(allowed)),
            )
            for offset, ch in letters
            if ch not in allowed
        ]
        used = {ch for _, ch in letters}
        unused = sorted(allowed - used) if params.require_all else []
        violations += [
            Violation(rule="unused_name_letter", offset=None, found="", expected=ch)
            for ch in unused
        ]
        total = len(letters) + len(unused)
        return self._report(
            good=total - len(violations),
            total=total,
            violations=violations,
            metrics={
                "letters": float(len(letters)),
                "outside": float(len(violations) - len(unused)),
                "unused_name_letters": float(len(unused)),
            },
        )
```

- [ ] **Step 5: Run to verify they pass.**

- [ ] **Step 6: Write the fixtures**

```yaml
# src/denckring/eval/fixtures/golden/prisoners_constraint.yaml
procedure: prisoners_constraint
lang: en
cases:
  - name: within-x-height
    source: constructed example; the constraint is Perec's, in Oulipo, Atlas (1981)
    text: no one saw our man swim across, nor came near
    params: {}
    satisfied: true
  - name: ordinary-prose
    source: constructed counterexample
    text: the tall dog leapt
    params: {}
    satisfied: false
```

```yaml
# src/denckring/eval/fixtures/golden/beau_present.yaml
procedure: beau_present
lang: en
cases:
  - name: dedication-within-the-name
    source: constructed example; the form is Perec's, in Oulipo, Atlas (1981)
    text: a calm camel came
    params: { name: Marcel }
    satisfied: true
  - name: strays-outside-the-name
    source: constructed counterexample
    text: a zebra came
    params: { name: Marcel }
    satisfied: false
```

Before committing, run `uv run denckring check prisoners_constraint <(printf '%s' "no one saw our man swim across, nor came near")` to confirm the constructed example really conforms; adjust the wording until it does rather than weakening the checker.

- [ ] **Step 7: Write the strategies**

```python
# tests/strategies/prisoners_constraint.py
from hypothesis import strategies as st

_SAFE = "aceimnorsuvwxz"
_FORBIDDEN = "bdfghjklpqty"


def satisfying():
    return st.text(alphabet=_SAFE + " ", max_size=40).map(lambda text: (text, {}))


def violating():
    return st.tuples(st.text(alphabet=_SAFE, max_size=20), st.sampled_from(_FORBIDDEN)).map(
        lambda pair: (pair[0] + pair[1], {})
    )
```

```python
# tests/strategies/beau_present.py
from hypothesis import strategies as st

_NAME = "marcel"


def satisfying():
    return st.text(alphabet=_NAME + " ", max_size=40).map(lambda text: (text, {"name": _NAME}))


def violating():
    return st.tuples(st.text(alphabet=_NAME, max_size=20), st.sampled_from("bdfgh")).map(
        lambda pair: (pair[0] + pair[1], {"name": _NAME})
    )
```

- [ ] **Step 8: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A
git commit -m "feat: add prisoner's constraint and beau présent procedures"
```

---

### Task 14: acrostic and telestich

**Files:**
- Create: `src/denckring/procedures/{acrostic,telestich}.py`, matching fixtures, strategies and tests.

**Interfaces:**
- Consumes: `line_spans`, `word_spans`, `letter_spans`.
- Produces: `AcrosticParams(target: str, unit: Literal["line", "word"] = "line")`; `Telestich` reuses the same params model and overrides which letter of each unit is taken.

- [ ] **Step 1: Scaffold both, delete the duplicate catalogue rows.**

- [ ] **Step 2: Write the tests**

```python
# tests/test_acrostic.py
import pytest

from denckring import check
from denckring.core.errors import InvalidParams

CARROLL = """A boat beneath a sunny sky
Lingering onward dreamily
In an evening of July
Children three that nestle near
Eager eye and willing ear"""


def test_carroll_acrostic_is_satisfied():
    assert check("acrostic", CARROLL, target="ALICE").satisfied


def test_wrong_initial_is_a_violation():
    report = check("acrostic", "Apple\nZebra", target="AB")
    assert not report.satisfied
    assert report.violations[0].found == "z"
    assert report.violations[0].expected == "b"


def test_too_few_lines_is_a_violation():
    report = check("acrostic", "Apple", target="AB")
    assert not report.satisfied
    assert any(v.rule == "missing_unit" for v in report.violations)


def test_extra_lines_are_a_violation():
    report = check("acrostic", "Apple\nBerry\nCherry", target="AB")
    assert not report.satisfied
    assert any(v.rule == "extra_unit" for v in report.violations)


def test_word_unit_uses_word_initials():
    assert check("acrostic", "alpha bravo", target="ab", unit="word").satisfied


def test_missing_target_is_an_invalid_params_error():
    with pytest.raises(InvalidParams):
        check("acrostic", "text")
```

```python
# tests/test_telestich.py
from denckring import check


def test_final_letters_spell_the_target():
    assert check("telestich", "beta\nzero\nomen", target="aon").satisfied


def test_wrong_final_letter_is_a_violation():
    assert not check("telestich", "beta\nzero", target="ab").satisfied
```

- [ ] **Step 3: Run to verify they fail.**

- [ ] **Step 4: Write the checkers**

```python
# src/denckring/procedures/acrostic.py
"""Acrostic — the initial letters of the units spell a target."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans, word_spans


class AcrosticParams(BaseModel):
    target: str = Field(description="The word or phrase the unit letters must spell.")
    unit: Literal["line", "word"] = Field(default="line", description="What carries a letter.")

    @field_validator("target")
    @classmethod
    def _at_least_one_letter(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("target must contain at least one letter")
        return value


@register
class Acrostic(BaseProcedure[AcrosticParams]):
    id = "acrostic"
    #: Index into each unit's letters. Telestich overrides it with -1.
    letter_index = 0

    @classmethod
    def params_model(cls) -> type[AcrosticParams]:
        return AcrosticParams

    def _units(self, text: str, pack: LanguagePack, unit: str) -> list[tuple[int, str]]:
        return line_spans(text) if unit == "line" else word_spans(text, pack)

    def _check(self, text: str, pack: LanguagePack, params: AcrosticParams) -> Report:
        expected = [pack.fold_diacritics(ch) for ch in params.target if ch.isalpha()]
        units = self._units(text, pack, params.unit)
        actual: list[tuple[int, str]] = []
        for offset, unit_text in units:
            letters = letter_spans(unit_text, pack)
            if letters:
                local_offset, letter = letters[self.letter_index]
                actual.append((offset + local_offset, letter))

        violations: list[Violation] = []
        matches = 0
        for index, want in enumerate(expected):
            if index >= len(actual):
                violations.append(
                    Violation(rule="missing_unit", offset=None, found="", expected=want)
                )
                continue
            offset, got = actual[index]
            if got == want:
                matches += 1
            else:
                violations.append(
                    Violation(rule="wrong_letter", offset=offset, found=got, expected=want)
                )
        for offset, got in actual[len(expected) :]:
            violations.append(
                Violation(rule="extra_unit", offset=offset, found=got, expected="")
            )

        total = max(len(expected), len(actual))
        return self._report(
            good=matches,
            total=total,
            violations=violations,
            metrics={
                "target_length": float(len(expected)),
                "units": float(len(actual)),
                "matches": float(matches),
            },
        )
```

```python
# src/denckring/procedures/telestich.py
"""Telestich — the final letters of the units spell a target."""

from __future__ import annotations

from denckring.core.registry import register
from denckring.procedures.acrostic import Acrostic


@register
class Telestich(Acrostic):
    id = "telestich"
    letter_index = -1
```

- [ ] **Step 5: Run to verify they pass.**

- [ ] **Step 6: Write the fixtures**

```yaml
# src/denckring/eval/fixtures/golden/acrostic.yaml
procedure: acrostic
lang: en
cases:
  - name: carroll-alice
    source: Lewis Carroll, A Boat Beneath a Sunny Sky (1871), opening stanza
    text: |-
      A boat beneath a sunny sky
      Lingering onward dreamily
      In an evening of July
      Children three that nestle near
      Eager eye and willing ear
    params: { target: ALICE }
    satisfied: true
  - name: wrong-initials
    source: constructed counterexample
    text: |-
      Apple
      Zebra
    params: { target: AB }
    satisfied: false
```

```yaml
# src/denckring/eval/fixtures/golden/telestich.yaml
procedure: telestich
lang: en
cases:
  - name: final-letters-spell-aon
    source: constructed example; the form is described in Puttenham (1589)
    text: |-
      beta
      zero
      omen
    params: { target: aon }
    satisfied: true
  - name: wrong-finals
    source: constructed counterexample
    text: |-
      beta
      zero
    params: { target: ab }
    satisfied: false
```

- [ ] **Step 7: Write the strategies**

```python
# tests/strategies/acrostic.py
from hypothesis import strategies as st

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_TAIL = st.text(alphabet=_ALPHABET, max_size=5)


def satisfying():
    return st.lists(st.sampled_from(_ALPHABET), min_size=1, max_size=6).flatmap(
        lambda target: st.lists(_TAIL, min_size=len(target), max_size=len(target)).map(
            lambda tails: (
                "\n".join(t + tail for t, tail in zip(target, tails, strict=True)),
                {"target": "".join(target)},
            )
        )
    )


def violating():
    return st.lists(_TAIL, min_size=2, max_size=4).map(
        lambda tails: ("\n".join("z" + tail for tail in tails), {"target": "a" * len(tails)})
    )
```

```python
# tests/strategies/telestich.py
from hypothesis import strategies as st

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_HEAD = st.text(alphabet=_ALPHABET, max_size=5)


def satisfying():
    return st.lists(st.sampled_from(_ALPHABET), min_size=1, max_size=6).flatmap(
        lambda target: st.lists(_HEAD, min_size=len(target), max_size=len(target)).map(
            lambda heads: (
                "\n".join(head + t for t, head in zip(target, heads, strict=True)),
                {"target": "".join(target)},
            )
        )
    )


def violating():
    return st.lists(_HEAD, min_size=2, max_size=4).map(
        lambda heads: ("\n".join(head + "z" for head in heads), {"target": "a" * len(heads)})
    )
```

- [ ] **Step 8: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
uv run denckring eval --all
git add -A
git commit -m "feat: add acrostic and telestich procedures"
```

---

### Task 15: Catalogue expansion, README, final verification

**Files:**
- Modify: `src/denckring/data/catalogue.yaml` (add the catalogued-only rows)
- Create: `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Test: `tests/test_readme.py`

**Interfaces:**
- Consumes: everything.
- Produces: the finished deliverable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_readme.py
from pathlib import Path

from denckring import check, list_procedures
from denckring.eval import harness

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_example_runs_as_written():
    report = check("lipogram", "This is a small conforming bit of writing", forbidden="z")
    assert report.satisfied


def test_all_twelve_batch_one_procedures_are_registered():
    expected = {
        "acrostic",
        "beau_present",
        "heterogram",
        "lipogram",
        "palindrome",
        "pangram",
        "prisoners_constraint",
        "reverse_snowball",
        "snowball",
        "tautogram",
        "telestich",
        "univocalic",
    }
    assert set(list_procedures()) == expected


def test_catalogue_is_larger_than_the_implemented_set():
    coverage = harness.status()
    assert coverage.catalogued > coverage.implemented
    assert coverage.implemented == coverage.validated == 12


def test_readme_mentions_the_licence_split():
    text = README.read_text(encoding="utf-8")
    assert "MIT" in text
    assert "CC BY 4.0" in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_readme.py -v`
Expected: FAIL on `test_catalogue_is_larger_than_the_implemented_set` and the README tests.

- [ ] **Step 3: Add the catalogued-only rows**

Append to `src/denckring/data/catalogue.yaml`, in the same shape as the existing rows, with `languages: [en]` unless noted. Every row needs `names.en`, `definitions.en`, `source`, `kind`, `requires` and `prompt_hints.en`.

| id | kind | requires | source |
|---|---|---|---|
| `n_plus_7` | both | `tokens, lexicon.nouns` | Jean Lescure, in Oulipo, La Littérature potentielle (1973) |
| `s_plus_7` | both | `tokens, lexicon.nouns` | Oulipo, La Littérature potentielle (1973) |
| `anagram` | both | `tokens` | Traditional; Lycophron (3rd century BC) |
| `larding` | both | `tokens` | Oulipo, Atlas de littérature potentielle (1981) |
| `definitional_literature` | both | `tokens, lexicon.nouns` | Marcel Bénabou and Georges Perec, littérature définitionnelle (1966) |
| `cut_up` | constructive | `tokens` | Brion Gysin and William S. Burroughs, Minutes to Go (1960) |
| `fold_in` | constructive | `tokens` | William S. Burroughs, The Third Mind (1978) |
| `diastic` | both | `tokens` | Jackson Mac Low, Stanzas for Iris Lezak (1972) |
| `mesostic` | both | `tokens` | John Cage, Writing Through Finnegans Wake (1978) |
| `syllable_count` | restrictive | `tokens, syllables` | Traditional prosody |
| `alexandrine` | restrictive | `tokens, syllables` | French classical prosody; Racine |
| `blank_verse` | restrictive | `tokens, syllables` | Henry Howard, Earl of Surrey, translation of the Aeneid (1554) |
| `rhyme_scheme` | restrictive | `tokens, phonemes` | Traditional prosody |
| `sonnet` | restrictive | `tokens, syllables, phonemes` | Giacomo da Lentini, Sicilian School (c. 1230) |
| `haiku` | restrictive | `tokens, syllables` | Matsuo Bashō (17th century); named by Masaoka Shiki (1892) |
| `terza_rima` | restrictive | `tokens, phonemes` | Dante Alighieri, Commedia (c. 1320) |
| `denckring` | constructive | `tokens, lexicon.syllables` | Georg Philipp Harsdörffer, Fünffacher Denckring der Teutschen Sprache (1651), languages: [de] |
| `proteus_verse` | constructive | `tokens` | Julius Caesar Scaliger, Poetices libri septem (1561) |
| `wechselsatz` | constructive | `tokens` | Quirinus Kuhlmann, Der Wechsel Menschlicher Sachen (1671), languages: [de] |

These rows are `catalogued` only. They must not have modules, and `test_catalogue_is_larger_than_the_implemented_set` proves the coverage metric measures a real gap.

- [ ] **Step 4: Write the README**

Open with the runnable three-line example, not a manifesto:

````markdown
# denckring

A library of experimental writing procedures — lipograms, snowballs, acrostics and
several hundred more — where **the validator is the eval**.

```python
from denckring import check

report = check("lipogram", "A small conforming bit of writing", forbidden="z")
print(report.satisfied, report.score)
```

```console
$ denckring check snowball poem.txt
$ denckring status
31 catalogued · 12 implemented · 12 validated
```

Every procedure pairs a generator with a validator, and the acceptance criterion is
intrinsic: a lipogram either contains the forbidden letter or it does not. That makes
the catalogue unusually well suited to automated work — the check *is* the test.

## Install

```console
pip install denckring          # English, no data files
pip install denckring[de]      # German (not yet released)
pip install denckring[fr]      # French (not yet released)
```

## What's here

Batch 1 implements the twelve procedures that need no lexicon: lipogram, univocalic,
tautogram, pangram, heterogram, palindrome, snowball, reverse snowball, prisoner's
constraint, beau présent, acrostic and telestich. The catalogue lists many more,
sourced and awaiting implementation — `denckring list --status catalogued`.

## Scope of the name

The *Fünffacher Denckring der Teutschen Sprache* (Harsdörffer, 1651) is one device
among the hundreds catalogued here, not the whole subject. Werkzeug is not only about
tools either. Searching for `oulipy` will also find this package.

## Licence

Code is MIT. The catalogue in `src/denckring/data/catalogue.yaml` is CC BY 4.0, with
per-entry source attribution, and is intended to be useful on its own.
````

Also write `CONTRIBUTING.md` stating the two hard rules — one module per procedure,
`check` mandatory — and pointing at `denckring new <id>`; and `CHANGELOG.md` in Keep a
Changelog form with an `Unreleased` section describing 0.1.0.

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS, everything.

- [ ] **Step 6: Run the full verification and show the output**

```bash
uv run pytest
uv run ruff format --check
uv run ruff check
uv run mypy --strict src tests
uv run denckring eval --all
uv run denckring status
uv run denckring list --status catalogued | head
```

Expected: four green tool runs, a green eval scoreboard covering twelve procedures, and
a status line whose `catalogued` count equals the number of rows in the catalogue.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: expand catalogue, add README, CONTRIBUTING and CHANGELOG"
```

---

## Self-review notes

Spec coverage was checked section by section. Every spec section maps to a task:
architecture → Tasks 2–5; the contract and `params_schema` → Task 4; scoring → Task 4's
`_report` and Task 10's `pangram` exception; closing the loop without a lexicon →
Task 6; the twelve procedures → Tasks 6 and 10–14; catalogue → Tasks 3 and 15; eval
harness levels 1–3 → Tasks 6 and 7; CLI → Tasks 8 and 9; error handling → Tasks 2, 5
and 8; acceptance → Task 15.

Two deliberate deviations from the seed, both recorded as ADRs: the catalogue lives
inside the package rather than at the repo root, because it must ship in the wheel
(ADR 0008); and `LanguagePack` gains `word_spans`, `alphabet`, `vowels`, `ascenders`
and `descenders` beyond the seed's four-method sketch, because Batch 1 needs offsets
and glyph shapes.

Names used consistently throughout: `check`, `_check`, `params_model`, `params_schema`,
`_report`, `letter_spans`, `word_spans`, `line_spans`, `get_pack`, `all_procedures`,
`implemented_ids`, `validated_ids`, `golden_cases`, `status`, `run`.
