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
- Combinatorial devices: ordered slots of alternatives, asked either to segment a word
  or to select one alternative per position. `denckring`, `cent_mille_milliards` and
  `wechselsatz` implemented on it, with Harsdörffer's 1651 rings shipped in core.
  `denckring` also generates, so spinning the rings round-trips through its own checker.
- Catalogue rows for `ars_combinatoria` and `llull_figure`, the tradition the Denckring
  descends from.
- ADR 0017 on a device's data shipping with its procedure.
- `attested` on every catalogue entry: `author-stated`, `codified` or `reconstruction`.
  It records whether anyone ever set the procedure down as a rule, which `attribution`
  — about how the source was established — does not answer.
- `serial_lipogram`, the whole-work form attributed to Tryphiodorus and excerpted by
  Jean Paul in 1783.
- ADR 0018 on attestation.
- `notes` on catalogue entries, for contested figures, reception history and caveats —
  so a definition can go back to being a definition.
- Combinatory figures: an alphabet read at several levels at once. Llull's ternary Ars
  ships with all six of its tables, and Kircher's Ars Magna Sciendi as a preset of the
  same mechanism. `llull_figure` checks and generates chambers; counts are computed
  from the letters (84 ternary chambers, 36 pairs) rather than quoted.
- A corpus layer: `Corpus`, `Entry` and a parser reading JSON or plain text. No corpus
  ships with the package — the loader is here, the reading is the reader's.
- `ideenwuerfeln`, reconstructed from Jean Paul's notebook of February 1795, and
  `witz_metaphor` catalogued as the step it stops short of. The first entries to carry
  `attested: reconstruction`.
- ADR 0020 on corpora not being shipped.
- `pasigraphy`, Kircher's universal writing: a sentence sent across a numbered
  vocabulary, with the losses counted rather than smoothed — words with no number,
  numbers with no entry at the far end, and words reachable from several numbers,
  where two distinct things arrive as one. The vocabulary is supplied by the caller.
- `arca_musarithmica`: a phrase is measured, the tablet for that length is found, and
  the chosen pattern must be one that tablet offers. The patterns are never read, so
  Kircher's pitch numbers and a set of stress patterns work equally well in the same
  table. No tablet ships.
- ADR 0021 on implementing the transferable part of a procedure rather than the
  artefact.

### Fixed

- Two language packs claiming one language were resolved silently by load order. They
  now raise `DuplicatePack` naming both, since answers that depend on installation
  order are the failure ADR 0004 exists to prevent.
- A report could say satisfied and still list violations, when a violation was appended
  without being counted in the score. The invariant suite asserted
  `satisfied == (score == 1.0)` from the start but never that a satisfied report is
  silent; it does now, and the Arca's tone check was the case that showed the gap.
- `apply` let Pydantic's validation error escape where `check` wrapped it in
  `InvalidParams`, so one kind of mistake raised two kinds of failure depending on
  which method you called. Both now go through one door.
- Three catalogue edits in earlier releases silently did nothing, because a string
  replacement that matches nothing succeeds quietly. The Denckring, Wechselsatz and
  Proteus-verse rows never received the text they were reported as having. All three
  are now written, and catalogue edits assert that they applied.
- The Denckring row overstated Harsdörffer, who labels the rings but states no total,
  and understated the case against the 97,209,600 the literature repeats. That figure
  factors as 2^8 x 3 x 5^2 x 61 x 83, and neither 61 nor 83 divides any ring size on
  any count — a stronger refutation than the divisibility argument it replaces. The row
  now also records that two independent counts of the parts disagree about one boundary
  while both coming to 264, and cites the Erquickstunden rather than the Poetischer
  Trichter, where the device is often wrongly placed.
- `denckring`, `cent_mille_milliards` and `wechselsatz` were filed as having no
  computable acceptance criterion. Asking whether a word is producible by five rings is
  a segmentation question, and asking whether a poem is one of Queneau's is a selection
  check; both are decidable. `line_permutation`, `stanza_permutation` and
  `word_permutation` keep their classification, because their definitions claim every
  ordering reads as a finished text and a permutation check does not verify that.
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
