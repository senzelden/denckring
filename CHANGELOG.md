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
- `belle_absente`: Perec's form, one line per letter of a dedicatee's name, each line
  omitting exactly that letter and using every other letter of the alphabet, so the
  missing letters read down the poem as the name itself.
- `serial_lipogram`: the whole-work form attributed to Tryphiodorus, as many parts as
  the alphabet has letters, the omitted letter walking one step per part. `paragraph_spans`
  in `core/text.py` gives a part more than one line to work with, the way Tryphiodorus's
  twenty-four books do.
- `pangrammatic_window`: the shortest naturally occurring stretch of text holding every
  letter of the alphabet, scored against a caller-stated `max_length` rather than a
  hidden constant — without a bar this is `pangram` under a second name.
- `paragram`, with a lexicon-gated generator: both halves of a one-letter word swap are
  left in the text for `check` to find, and `apply` ranks every candidate swap by
  pronounceability, noun membership and length instead of taking the first match.
  Checking needs no lexicon; generating does, so `apply` carries its own capability
  requirement rather than the catalogue row claiming one `check` never needed. The new
  `NoCandidateWord` error is raised when the search finds nothing to swap, rather than
  returning text with no swap in it for `check` to then reject.
- `dactylic_hexameter`: six feet, the first four either a dactyl or a spondee, the fifth
  a dactyl, and the sixth a spondee or trochee. This yields thirty-two readings spanning
  13–17 syllables.
- `elegiac_couplet`: a dactylic hexameter answered by a pentameter. The pentameter is two
  hemiepes; only the first admits the spondee. That asymmetry is the form.
- `sapphic_stanza`: three hendecasyllables and an adonic, 11/11/11/5.
- `alcaic_stanza`: two hendecasyllables, an enneasyllable and a decasyllable, 11/11/9/10.
- `double_dactyl`: two quatrains, with one line of the second being a single six-syllable
  word. The nonsense opening, the named person and the rhyme are not checked, and the
  docstring says so.
- `renga`: alternating 5-7-5 and 7-7 stanzas. Its `links` parameter is a minimum, not an
  exact count.
- `haibun`: prose and haiku alternating.
- The four new metrical procedures—`dactylic_hexameter`, `elegiac_couplet`, `sapphic_stanza`,
  `alcaic_stanza`—are checked as English accentual verse. Classical quantity is vowel length,
  which English does not have, so stress stands in for it. This is the batch's central
  editorial decision.
- `?` now means "either" on the pattern side as well as the word side—the classical anceps.
  Before, it was honoured only for a free monosyllable, so a pattern written with anceps
  rejected every fixed-stress word at that position. Sapphics and alcaics both need it.
- A word not in the pronouncing dictionary no longer aborts the scan. `pack.stress_patterns`
  raised `MissingCapability` for such a word—naming a capability the pack actually provides—so
  one ordinary English noun killed the whole check. Longfellow's own hexameter could not be
  checked. Unknown words now scan as free and are counted in a new `estimated_words` metric,
  mirroring the contract the syllable path has always had. **This changed previously deliberate
  behaviour:** a test named `test_an_unknown_word_raises_rather_than_guessing` was replaced.
  Callers who want strict scanning can reject on `estimated_words > 0`.
- `word_stress`, `feet` and `stanza_violations` added to `core/prosody.py`. `word_stress`
  handles the out-of-dictionary repair; `feet` enumerates substitutable foot readings, making
  a metre a set of readings rather than one; `stanza_violations` applies one pattern per line,
  since a sapphic changes shape from line to line.
- `estimated_words` now reported by all twelve form-report callers—`blank_verse`,
  `heroic_couplet`, `iambic_pentameter`, `limerick`, `petrarchan_sonnet`, `rhyme_royal`,
  `rhyme_scheme`, `shakespearean_sonnet`, `terza_rima`, `triolet`, `trochaic_tetrameter`,
  `villanelle`—where before it was computed and discarded.
- Catalogue rows for the five procedures that scan stress — the four metres and
  `double_dactyl` — gained `stress` in `requires`, since scanning stress reaches
  `pack.stress_patterns`. `renga` and `haibun` did not — they count syllables only.
- `describe(id)` and `summaries()` in core, returning the catalogue as a machine reads
  it: a definition, the prompt hints, whether this install can actually run the row and
  what it lacks if not, and the parameter schema as JSON Schema. Four callers needed
  this assembly — the CLI's `show`, the explorer, the MCP server and the skill — so it
  lives in one place rather than being computed four times and drifting four ways.
  `list_procedures()` is untouched: it is public and still returns `list[str]`.
- A stable `code` on all fourteen error classes and a `to_dict()` on the base, so a
  failure crosses a process boundary as `{"code": "invalid_params", "detail": {...}}`
  rather than as a traceback. A model can act on the first and cannot act on the second.
  `UnknownProcedure` additionally carries near-match `suggestions`, so a mistyped
  `lipogam` answers with `lipogram` instead of a dead end.
- `denckring describe <id> --json` and `denckring list --json`, so the skill and any
  other non-Python caller reach the same two functions the MCP server does. `--json`
  refuses to combine with `--kind` or `--status`, which filter the catalogue rather than
  the implemented set: the flag would otherwise be accepted and silently ignored.
- An MCP server behind `pip install denckring[mcp]`, run as `denckring-mcp`. It exposes
  four tools — `list_procedures`, `describe_procedure`, `check_text`, `apply_procedure`
  — taking the procedure as a parameter, rather than one tool per procedure. Eighty-six
  tool definitions would sit in every client's context, and model performance degrades
  sharply with tool count. No tool raises: each catches `DenckringError` and returns its
  dictionary form.
- A Claude Code skill at `skills/denckring/SKILL.md`, which shells out to the CLI and so
  needs no extra beyond the package. Both transports are deliberately thin — neither
  computes anything, so the two cannot disagree about what a procedure is.
- Twenty-eight procedures implemented, taking the total from 86 to 114. Eleven fixed
  forms: `sonnet`, `ottava_rima`, `spenserian_stanza`, `ballade`, `rondeau`, `ghazal`,
  `curtal_sonnet`, `englyn`, `clerihew`, `alliterative_verse`, `assonance_constraint`.
  Three clusters of source-comparison rows: letter-class (`homoconsonantism`,
  `homovocalism`), selection (`diastic`, `mesostic`, `column_reading`, `haikuization`)
  and rearrangement (`boustrophedon`, `text_folding`, `mathews_algorithm`). And a
  remainder: `fold_in`, `univocalic_translation`, `lipogrammatic_translation`,
  `larding`, `multiple_constraint`, `tmesis`, `spoonerism`, `word_ladder`.
- `core/source_compare.py`: `letter_class_report`, `selection_report` and
  `rearrangement_report`, the three shapes eight of this batch's rows share. Each was
  extracted from a row already written, not designed ahead of one — `homoconsonantism`
  was written by hand first, and writing `homovocalism` against that code showed the
  entire body was identical but for one predicate, which is why `letter_class_report`
  exists at all. Precedent: `form_report`, extracted from real sonnets the same way.
- `lines=` on `form_report`, so a fixed form with a prescribed length reports
  `wrong_line_count` and stops rather than scanning a scheme or metre against lines
  that are already the wrong ones — matching `stanza_violations`'s existing behaviour.
- `multiple_constraint`, Oulipo's general composite-constraint form. It replaces
  `univocalic_lipogram_pair`, whose definition described any composite constraint
  rather than the one pair its id named. `denckring search` finds the row under the old
  id, under the old id written as prose, and under the row's previous published English
  name, *Compound constraint*; all three are carried as aliases. `denckring show
  univocalic_lipogram_pair` still raises `UnknownProcedure`, because `registry.get`
  resolves ids and never consults aliases — but it names `multiple_constraint` as the
  suggestion.
- German declared on seventeen rows, each decided on whether the procedure *means*
  something in German rather than whether it merely runs, and each shipping a German
  golden fixture — a declaration with no fixture behind it is an assertion, not a claim.
  Every one also carries `names.de` and `definitions.de`, so the German a row claims
  appears in the row a German reader reads, and a test in the catalogue quality suite
  requires that of every declared language. `semordnilap`, which declared `de` with no
  German name since long before this batch, is corrected with them.
- `tests/test_requires_honesty.py`, guarding `requires` in both directions. One test
  watches through the real `check()` path whether a row's golden fixtures ever reach the
  capabilities it declares; it caught `limerick` on its first run against every
  implemented procedure, not just this batch's. The other runs each row's own fixtures
  against a pack carrying exactly what the row declares and nothing more, so a row that
  reaches further than it promised raises rather than passing quietly on the full `en`
  pack. Their shared blind spot, documented in the module: a row that calls a
  capability's method and discards the answer is invisible to both — the gap
  `haikuization` fell into below.

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
- Six form rows published a capability contract their own code broke. `sonnet`,
  `ottava_rima`, `ballade`, `curtal_sonnet` and `spenserian_stanza` declared
  `[tokens, phonemes, syllables]`; run against a pack carrying exactly that, all five
  raised `MissingCapability('stress')`. Scanning metre reaches `stress`
  (`prosody.word_stress` → `pack.stress_patterns`) and reaches syllable counting only on
  the out-of-dictionary fallback, which is `syllables.heuristic`; nothing in this
  codebase calls `pack.syllables()` at all. All five now declare
  `[tokens, phonemes, stress, syllables.heuristic]`, the shape `double_dactyl` already
  used, and `englyn` — which is syllabic, not accentual — declares
  `[tokens, syllables.heuristic, phonemes]`.
- The catalogue got more honest in both directions this batch. Rows that understated
  what they need: `word_ladder` and `tmesis` gained `lexicon.words`. Six rows that reach
  `pack.vowels()`, most of them through `letter_class_report`, gained `alphabet`:
  `univocalic`, `bivocalic`, `monoconsonantal`, `homoconsonantism`, `homovocalism` and
  `univocalic_translation`. `dactylic_hexameter` gained
  `syllables.heuristic`, which any metre scan falls back on for a word the pronouncing
  dictionary does not carry. Rows that declared what they never used: `limerick` dropped `stress` — it checks the rhyme scheme only, never the
  anapestic metre or shortened couplet its definition names; `prisoners_constraint`
  dropped `tokens` and `fold_diacritics` — it scans raw characters and asks only about
  x-height, and folding first would destroy the ascender the check needs to see;
  `spoonerism` dropped `fold_diacritics` — its onset comparison lives entirely in
  phonemes, where accents do not apply — and gained `alphabet`, which its written-onset
  guess does call. `haikuization` is the interesting one: it
  gained `phonemes` early in the batch on the assumption that a rhyme-word reading and
  a line-end reading could be told apart, then lost it again, because this codebase's
  rhyme machinery always resolves a line to its final word regardless of whether it
  pronounces as a rhyme with anything — the two readings are not constructible here, so
  the capability did no work and only made the row refuse unusual vocabulary.
- `back_translation`, `transduction` and `intralingual_translation` reclassified to
  `checkability: none`, each recording in `notes` why no acceptance criterion exists
  rather than merely asserting it: a translated-onward-and-back rendering, a chain of
  translations whose drift is the point, and a rewording into another register have no
  independent text to check the result against. `implementable` falls from 129 to 126
  as a result — the fall is the point, not a regression.
- Four catalogue rows are blocked on a missing capability and now say so in `notes`:
  `homosyntaxism` and `verbless_prose` need a part-of-speech capability no pack
  provides; `homophonic_translation` needs phonemes in two languages at once;
  `perverb` needs a proverb corpus, which ADR 0020 already rules this project does not
  ship.

[Unreleased]: https://github.com/senzelden/denckring/commits/main
