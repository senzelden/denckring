# Repo Seed — a Python library of experimental writing procedures

English-first, German second, French third. Published on PyPI, showcased on GitHub.
The Verlagsspiel is one consumer among others, not the reason the package exists.

---

## 0. What changed from the first draft

The earlier sketch used German identifiers (`pruefe`, `Befund`, `wende_an`). For a package
intended for PyPI and a public repository that is a straightforward adoption barrier, and
it was wrong. **The API is English. The content is multilingual.** German and French live
in the data and the language packs, never in the function names.

---

## 1. Core idea

**Every procedure is a pair of generator and validator, and the validator is the eval.**

The rule for agentic development — give the agent a check it can run so the loop closes
without you as verifier — normally requires inventing a test. Here it doesn't. A lipogram
either contains the forbidden letter or it doesn't. A snowball grows by exactly one letter
per word or it doesn't. The acceptance criterion is intrinsic to the procedure.

Consequences: `check()` is mandatory, `apply()` optional; a procedure without a checker is
not registered; and the codebase is unusually well suited to unattended agent work, because
it is hundreds of small independent modules with no shared state and no ordering
dependencies.

---

## 2. Name

**`denckring`** — after Harsdörffer's Fünffacher Denckring der Teutschen Sprache (1651).

Nine characters, two syllables, one token, no umlaut, no ambiguous cluster. It matches the
shape of the most-installed single-token packages (median 8 chars, 87% at three syllables or
fewer) and it behaves like `werkzeug` at rank 151: an opaque foreign word that stops being a
word and becomes a brand. As a search term it is unique — nothing else on the internet is
called this.

Register alongside it:

- **`denkring`** — the modern spelling, which is what people will actually type. Defensive
  registration pointing at the same project.
- **`oulipy`** — the term people will search for. Alias in the docs.

Rejected and why: `clinamen` and `ouvroir` are taken; `combinatoria` and `officina` are four
to five syllables and read as monuments; `oulipo` is a living organisation's name and
mislabels the non-Oulipian half of the catalogue; `harsdoerffer` fails on umlaut
transliteration and a double-f; `cento` collides cognitively with CentOS and is unsearchable.

The scope caveat stands and belongs in the README: the Denckring is one device, the library
is hundreds of procedures. Werkzeug is not only about tools either.

## 3. Protocol

```python
# denckring/core/protocol.py
from typing import Protocol, Literal, runtime_checkable
from pydantic import BaseModel

Lang = Literal["en", "de", "fr"]
Kind = Literal["constructive", "restrictive", "both"]


class Violation(BaseModel):
    rule: str  # "forbidden_letter", "syllable_count"
    offset: int | None  # character offset when localisable
    found: str
    expected: str
    note: str | None = None


class Report(BaseModel):
    procedure: str
    satisfied: bool
    score: float  # 0.0–1.0, monotone — not merely binary
    violations: list[Violation]
    metrics: dict[str, float]  # free-form, e.g. {"mean_syllables": 12.04}


class Meta(BaseModel):
    id: str  # "lipogram", "n_plus_7", "denckring"
    names: dict[Lang, str]
    definitions: dict[Lang, str]
    source: str  # Perec, La Disparition (1969)
    kind: Kind
    languages: list[Lang]  # which languages the procedure supports
    requires: list[str]  # language-pack capabilities, see §4
    deterministic: bool
    prompt_hints: dict[Lang, str]


@runtime_checkable
class Procedure(Protocol):
    meta: Meta

    def check(self, text: str, *, lang: Lang = "en", **params) -> Report: ...
    # optional, only when kind in {"constructive", "both"}
    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params) -> str: ...
```

`score` is continuous on purpose. Binary pass/fail is useless for driving a retry loop; a
caller needs to know whether a text missed by one word or by fifty.

---

## 4. Language packs — the real architectural problem

Multilingualism here is not a translation layer. Procedures behave differently per language
in ways that touch the algorithm:

- **Lipogram** in French must decide whether `é`, `è`, `ê` count as `e`. They do. In German
  the analogous question is `ä`/`ae`.
- **N+7** needs a noun lexicon per language, and German needs compound handling on top.
- **Prisoner's constraint** (no ascenders or descenders) depends on the alphabet's shapes,
  so the forbidden set differs per orthography.
- **Syllable counting** and metre differ radically across the three.

So the language layer is an interface, not a dictionary:

```python
class LanguagePack(Protocol):
    lang: Lang
    capabilities: frozenset[str]  # {"tokens", "syllables", "lexicon.nouns", "phonemes"}

    def tokenize(self, text: str) -> list[str]: ...
    def syllables(self, word: str) -> list[str]: ...
    def nouns(self) -> Iterable[str]: ...
    def fold_diacritics(self, ch: str) -> str: ...
```

Each procedure declares `requires`. Calling a procedure with a pack that lacks a capability
raises `MissingCapability` with an actionable message — never a silently wrong result. That
single rule is what makes the package trustworthy across languages.

**Packaging:** English support ships in core with zero heavy dependencies. German and French
are extras — `pip install denckring[de]`, `[fr]`, `[all]` — carrying their lexicons and
hyphenation data. Third parties can register their own pack via an entry point, which is
what makes the library genuinely extensible rather than merely trilingual.

---

## 5. Catalogue vs implementation

Two different things:

| | Catalogue | Implementation |
|---|---|---|
| What | 500+ procedures as data | the subset that is code |
| Where | `data/catalogue.yaml` → SQLite | `denckring/procedures/<id>.py` |
| Holds | names, definitions, sources, languages | `check` / `apply` + tests |
| Grows by | reading and research | agent work, in batches |

Status per entry: `catalogued` → `implemented` → `validated` (has golden examples).

**Coverage is the project metric.** `denckring status` prints
`427 catalogued · 58 implemented · 41 validated`, and that is also the acceptance criterion
for an unattended run.

Publish the catalogue as **open data** in its own right. The research showed the field is
littered with one-off toys and unlicensed word lists; a clean, sourced, CC BY catalogue of
500 procedures would be a contribution independent of the code, and it is the thing most
likely to get the repository noticed.

---

## 6. Layout

```
src/denckring/
  core/         protocol.py  registry.py  errors.py  text.py
  lang/         base.py  en.py  de.py  fr.py
  procedures/   lipogram.py  snowball.py  n_plus_7.py  ...
  eval/         harness.py  report.py  fixtures/{golden,corpus}/
  cli.py
data/           catalogue.yaml
docs/           mkdocs, auto-generated gallery
tests/
```

One module per procedure. No collector modules — they create merge surface between
parallel agent runs.

---

## 7. Eval harness

**Level 1 — golden examples.** Per procedure, at least one genuine literary instance that
must return `satisfied=True` and one counterexample that must return `False`. This catches
misimplementations that property tests slide past.

**Level 2 — property tests (hypothesis).** The central invariant is round-tripping:
`check(apply(text))` is satisfied, for any input. That single property ties generator to
validator and makes every constructive procedure self-verifying. Plus determinism under
fixed seed, and per-procedure invariants like token-count preservation for N+7.

**Level 3 — suite scoreboard.** `denckring eval --all --json` runs every registered procedure
across the corpus fixtures in every declared language, reports pass rate and coverage, and
exits non-zero on regression. This is the CI gate and the agent's acceptance criterion.

**The fixtures are the documentation.** Generate the docs gallery from the golden examples,
so every procedure page shows a real input, a real output and a real report with zero extra
maintenance. That is also the showcase — a gallery of 500 procedures with worked examples
is far more compelling on a repo page than a feature list.

---

## 8. Open-source practices

**Build and quality**
- `src/` layout, `pyproject.toml`, hatchling, uv for dev; Python 3.11+
- ruff (lint + format), mypy strict, pytest + hypothesis + coverage, pre-commit
- `py.typed` marker — a typed API is a large part of perceived quality
- Core has near-zero runtime dependencies; everything optional lives behind extras

**CI/CD (GitHub Actions)**
- matrix across supported Pythons and the three OSes; lint, typecheck, test, build
- release on tag via **Trusted Publishing (OIDC)** — no PyPI API tokens in repo secrets
- attestations enabled on publish
- Dependabot for actions and deps

**Repository hygiene**
- README that opens with a runnable three-line example, not a manifesto
- CHANGELOG following Keep a Changelog; SemVer; a documented deprecation policy
- CONTRIBUTING that states the two hard rules (one module per procedure, `check` mandatory)
  and points at `denckring new <id>`
- CODE_OF_CONDUCT, issue and PR templates, `SECURITY.md`
- mkdocs-material + mkdocstrings on GitHub Pages
- `CITATION.cff` and a Zenodo DOI on release — this package has an academic audience, and
  being citable is cheap to arrange and disproportionately valuable for adoption

**Licensing — dual, deliberately**
- Code: MIT (or Apache-2.0 if you want the patent grant)
- Catalogue data: CC BY 4.0, with per-entry source attribution
- Language packs: audit separately. Wiktionary-derived data is CC BY-SA and share-alike
  attaches; pyphen is GPL/LGPL/MPL tri-licensed; keep anything copyleft behind an extra so
  the core stays permissive. Record this in an ADR before the first lexicon lands.

---

## 9. Working agreement for Claude Code

**AGENTS.md / CLAUDE.md stays short**: stack, the command `uv run denckring eval --all`, the
one-module-per-procedure rule, and a pointer to the skill. Everything conditional goes in a
skill so it loads only when relevant.

**A skill `new-procedure`** carries the actual contract: protocol, naming, test obligations,
language-pack capability declaration, worked example module.

**Deterministic scaffolding, not freehand.** `denckring new <id>` emits module, test file,
catalogue row and fixture stub from templates. The agent fills in logic and invents no
structure — the same lesson as the Atlassian conversion scripts.

**Batch rhythm.** One run = ten procedures, `/clear` between batches, milestone demo rather
than per-decision approval:

> Implement the next ten catalogued procedures with `kind: restrictive` and
> `languages: ["en"]`. The run is done when `uv run denckring eval --all` is green and
> `denckring status` shows ten more `validated`.

Fully closed brief, no questions back — the right shape for unattended runs.

**Language expansion is its own batch type**: "add `de` support to the twelve procedures
that currently declare only `en`, extending the fixtures accordingly." Also closed, also
verifiable.

---

## 10. Quick wins

**Batch 1 — pure restrictions, no data, no lexicon, no model.** Twenty to forty lines each,
English only at first. Lipogram · univocalic · tautogram · pangram · heterogram ·
palindrome · snowball (rhopalic) · reverse snowball · prisoner's constraint · beau présent ·
acrostic · telestich. The harness stands up and is proven in an evening.

**Batch 2 — transformations needing a light lexicon.** N+7 / S+7 · anagram checker ·
larding · définitionnelle · cut-up · fold-in · diastic reading · mesostic.

**Batch 3 — form and sound (needs syllabification).** Syllable constraints · alexandrine ·
blank verse · rhyme-scheme checker · sonnet · haiku · terza rima.

**Batch 4 — the second language.** Take Batch 1 to German. Almost free, and it proves the
language-pack interface before it has to carry anything hard.

Denckring, proteus verse and Kuhlmann's Wechselsatz need ring data, lexicon filtering and
historical orthography. Milestone 3, not first, despite being what started this.

---

## 11. Consumers

The API should serve three shapes without favouring any:

1. **Library** — `from denckring import get; get("lipogram").check(text, lang="fr")`
2. **CLI** — `denckring check lipogram --lang fr text.txt --json` for pipelines
3. **Data contract** — stable JSON for `Report` and `Meta`, so non-Python callers can use it
   over HTTP without importing anything

The Verlagsspiel then becomes an ordinary consumer of (1) and (3): prompt hints from the
catalogue, a validation gate in the job queue that feeds `violations` back into the model for
one or two retries, and an objective sub-score for the weekly juries. Nothing game-specific
enters the package — no scoring curves, no genre coupling, no prize logic.

Keep the measurement internal on the game side: the colophon shows intent, as decided.

---

## 12. First ADRs

1. English API, multilingual content — and why
2. `check` mandatory, `apply` optional
3. Catalogue (data) separate from implementation (code); coverage as project metric
4. Language packs as capability-declaring plugins; `MissingCapability` over silent fallback
5. Continuous `score` rather than boolean
6. Dual licence: MIT code, CC BY catalogue; copyleft data confined to extras
7. One module per procedure; rationale is parallel agent runs
