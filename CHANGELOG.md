# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Core protocol: `Violation`, `Report`, `Meta` and the `LanguagePack` interface, all
  serialising to stable JSON for non-Python callers.
- `BaseProcedure`, a template method that validates language, capability and parameters
  before delegating, so a procedure module cannot forget those checks.
- Autodiscovering registry over `denckring.procedures`, enforcing one module per
  procedure with the module name equal to the procedure id.
- Catalogue of 31 sourced procedures in `src/denckring/data/catalogue.yaml`, licensed
  CC BY 4.0, as the single source of truth for procedure metadata.
- English language pack, shipping in core with no data files, declaring `tokens`,
  `alphabet`, `fold_diacritics` and `letter_shapes`.
- Batch 1 — twelve lexicon-free restriction procedures: `lipogram`, `univocalic`,
  `tautogram`, `pangram`, `heterogram`, `palindrome`, `snowball`, `reverse_snowball`,
  `prisoners_constraint`, `beau_present`, `acrostic`, `telestich`.
- Three-level eval harness: golden fixtures, Hypothesis strategies, and a scoreboard
  that exits non-zero on regression.
- CLI: `check`, `apply`, `list`, `show`, `status`, `eval`, `new`.
- `denckring new <id>`, which scaffolds module, test, strategy, fixture and catalogue
  row from templates.
- Eight architecture decision records under `docs/adr/`.
- German language pack, shipping in core with no data files and discovered through the
  `denckring.lang` entry-point group — the same path a third-party pack takes.
- `fold_diacritics`, a per-call parameter on the nine letter-comparing procedures,
  deciding whether `ä` counts as `a` and `ß` as `ss`. Defaults to true.
- `LanguagePack.exceeds_x_height`, and golden cases in German for all twelve procedures.
- Two further ADRs, 0009 and 0010, on the fold parameter and entry-point discovery.
- Catalogue grown from 31 to 145 sourced entries across eight families.
- `family`, `aliases` and `attribution` on every catalogue entry. `attribution`
  distinguishes a traced origin (`primary`) from a form documented in a standard
  reference (`reference`) from one with no single origin (`traditional`).
- `denckring search` matching ids, names and aliases; `denckring list --family`.
- `denckring catalogue export --format json|csv` emitting the dataset as a standalone
  file, and `LICENSE-DATA` carrying the CC BY 4.0 notice.
- A catalogue quality suite: every row must have a source, an English name, definition
  and prompt hint, a family and an attribution; aliases must be unique catalogue-wide
  and must not collide with any procedure id.

- `checkability` on every catalogue entry: `self`, `source`, or `none` for forms with
  no computable acceptance criterion. Coverage is now measured against the
  implementable subset, so `denckring status` no longer promises a gap that cannot
  close.
- 31 further procedures implemented, taking the total from 12 to 43 — letter and
  alphabet constraints, position and repetition constraints, the end-word forms
  (`sestina`, `quenina`, `pantoum`), and the source-relative procedures.
- `SourceParams` and `denckring check --source FILE`, for procedures decidable only
  against the text they were made from.
- `apply()` on `cut_up` and `every_nth_word`, and a round-trip suite asserting that
  `check(apply(text))` is satisfied — the seed's central property, deferred since the
  Batch 1 spec for want of any constructive procedure.
- `Constructive`, a runtime-checkable protocol for procedures that can generate.
- ADR 0011 on checkability.
- Syllable counting: `syllables.heuristic` in core, with `syllable_count` returning a
  count and whether it was looked up or estimated. Every syllabic report carries
  `metrics["estimated_words"]`.
- `denckring-en-data`, installed by `pip install denckring[en]`, adding
  `syllables.dictionary` from the CMU Pronouncing Dictionary (BSD-2-Clause, vendored).
  On Bashō's frog-pond haiku, core alone estimates 13 words; with the data package,
  none.
- Eight syllabic procedures: `haiku`, `tanka`, `senryu`, `cinquain`, `syllable_count`,
  `monosyllabic_prose`, `hendecasyllable`, `alexandrine`.
- ADRs 0012 and 0013 on the two syllable capabilities and on data as separate
  distributions.
- Rhyme and metre: `rhyme_key`, `rhyme_keys`, `stress_pattern` and `stress_patterns` on
  the data pack, plus the `stress` capability. Twelve procedures — `rhyme_scheme`,
  `iambic_pentameter`, `trochaic_tetrameter`, `blank_verse`, `heroic_couplet`,
  `terza_rima`, `villanelle`, `triolet`, `limerick`, `shakespearean_sonnet`,
  `petrarchan_sonnet`, `rhyme_royal`.
- Metre is checked as a satisfiability question: polysyllabic stress is fixed,
  monosyllabic stress is free, and every listed pronunciation is searched. These are
  the first procedures a core-only install genuinely cannot run — without
  `denckring[en]` they raise `MissingCapability` naming the extra.
- ADR 0014 on metre as satisfiability, and on what strict scansion does not accept.
- Release machinery: GitHub Actions CI (lint, typecheck, a 3×3 test matrix, a separate
  `denckring eval --all` gate, a core-only install job, a docs build and a distribution
  build), tag-triggered Trusted Publishing with attestations, and Dependabot.
- A generated documentation gallery: one page per catalogued procedure, built from the
  catalogue and the golden fixtures, so every worked example is one the test suite
  enforces.
- `CITATION.cff`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue and pull request templates,
  and a `.pre-commit-config.yaml` mirroring the CI lint and typecheck jobs.
- `lexicon.words` and `lexicon.nouns` capabilities, backed by WordNet's 55,239
  single-word noun lemmas (Princeton licence) added to `denckring-en-data`.
- Five procedures: `n_plus_7`, `s_plus_7`, `charade`, `semordnilap`, `word_square`.
  N+7 reports `ambiguous_words`, because a word list cannot tell you that *run* is a
  verb in this sentence.
- ADRs 0015 and 0016 on lexicon capabilities and on one data pack per language.
- `apps/explorer`, a local FastAPI browser for the catalogue and bench for the
  procedures. Outside the distribution: nothing published depends on it.

### Fixed

- Two language packs claiming one language were resolved silently by load order. They
  now raise `DuplicatePack` naming both, since answers that depend on installation
  order are the failure ADR 0004 exists to prevent.
- Thirteen catalogue rows declared `lexicon.nouns` when they wanted word membership,
  synonyms, antonyms or glosses. Each now names what it actually needs.
- Entry-point language packs were shadowed by the built-in English default, so an
  installed data package had no effect. Precedence is now explicit registration, then
  entry point, then built-in default.
- Unknown parameters passed to `check` were silently dropped, so a mistyped
  `--param frobidden=e` looked like a constraint being applied when it was not. They
  now raise `InvalidParams` naming the parameters the procedure actually accepts.
- Four catalogue rows misdescribed what they need: `boustrophedon` is decidable only
  against its source, and `semordnilap`, `kangaroo_word`, `word_square` and `charade`
  cannot be decided without a lexicon.
- `prisoners_constraint` compared folded letters, so it read `ß` as `ss` and `ä` as `a`
  and wrongly accepted *groß*, *Maße* and *Mädchen* — and English *naïve* with them. An
  ascender is a property of the written glyph, and folding destroys it. The checker now
  reads raw characters. **This changes existing English results:** text containing
  accented letters that previously satisfied the constraint no longer does.

[Unreleased]: https://github.com/senzelden/denckring/commits/main
