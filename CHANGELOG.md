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
- CLI: `check`, `apply`, `describe`, `list`, `search`, `show`, `status`, `eval`,
  `catalogue export`.
- `scripts/new_procedure.py`, which scaffolds module, test, strategy, fixture and
  catalogue row from templates. It is a contributor tool and stays outside the package:
  it writes into `src/denckring/procedures/` and appends to this repository's
  `catalogue.yaml`, so as the shipped `denckring new` it put a command in every user's
  CLI that could do nothing for them.
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
  German name since long before this batch, is corrected with them. `cent_mille_milliards`
  joins them from outside the batch: `check` already accepted a German poem against
  German strips while the catalogue still declared `languages: [en]`, an assertion wrong
  in the opposite direction from the others'. It now declares `languages: [en, de]` with
  `names.de` and `definitions.de`, backed by a German case pair in its golden fixture —
  a full fourteen-position poem the checker accepts, and the same poem with one line
  swapped for an alternative from a different position, which it does not — built from
  the real strips written for the stage scene. Rows declaring German: 38.
- `tests/test_requires_honesty.py`, guarding `requires` in both directions. One test
  watches through the real `check()` path whether a row's golden fixtures ever reach the
  capabilities it declares; it caught `limerick` on its first run against every
  implemented procedure, not just this batch's. The other runs each row's own fixtures
  against a pack carrying exactly what the row declares and nothing more, so a row that
  reaches further than it promised raises rather than passing quietly on the full `en`
  pack. Their shared blind spot, documented in the module: a row that calls a
  capability's method and discards the answer is invisible to both — the gap
  `haikuization` fell into below.
- `lexicon.glosses` on `LanguagePack`: every definition Open English WordNet records for
  a word, or an empty sequence when the lexicon cannot resolve it at all. Every sense,
  not the first — which sense a writer meant is not recoverable from the text, so a
  reader that accepts any of them is the honest one, the same reading `rhyme_keys` and
  `stress_patterns` already take. It costs 1.03 MB over shipping first senses only.
  Resolution tries the word as given, then its lemma, then plain `s`/`es` stripping;
  irregulars such as *went* stay out of reach by design and are disclosed rather than
  guessed at.
- `packages/denckring-en-data/scripts/build_lexicon.py`, the build the data package never
  had. `nouns.txt` was an opaque blob extracted by hand at some point in the past with no
  record of how; it is now generated, alongside `glosses.txt.gz` and a `metadata.json`
  carrying source, date and row counts, by a script in the repository. A test pins the
  shipped `nouns.txt` against what the script produces, so a hand-edit is caught rather
  than inherited.
- `kangaroo_word`: a word carrying a synonym of itself inside its own letters, in order
  (*encourage* carries *urge*). It needed no thesaurus — the synonym is a `synonym`
  parameter, the writer's claim, and what the row decides is the decidable half: that the
  claimed synonym is a real word, hidden in order, and not the word itself.
- `definitional_expansion`: each substantive word of the source replaced once by one of
  its dictionary definitions. The comparison was chosen by running it against real gloss
  text rather than at the desk — glosses carry parentheses, semicolons and colons no
  writer retypes character for character, so a gloss counts as present when its own
  lower-cased tokens appear as a contiguous run, punctuation and case folded away, word
  choice and word order kept. Occurrences are counted rather than merely found: a word
  appearing twice needs two expansions, and each match consumes the span it used.
- `definitional_literature`: the same procedure fed back into itself, which is the form
  Bénabou and Perec described. `check` is given the source and the finished text and
  nothing in between, so it discovers the depth — one round, then two, then three — and
  reports the first that accounts for every resolvable source word in an `iterations`
  metric. Below the top level a round means "some gloss of this word has all of its own
  substantive words present one round shallower"; word order is checked where the gloss
  must appear as a run and not below that, because pinning the nesting positions would
  mean parsing a text where every definition is stitched to the next with nothing between
  them. The cap of three rounds is measured, not guessed: against a genuine three-round
  expansion of *the cat sat* (3,679 tokens), depth 3 takes 0.15 s, depth 4 takes 18 s and
  depth 5 takes 219 s, because the cost falls on the searches that fail and cannot stop
  early.
- `lexicon.synonyms` and `lexicon.antonyms` were specified, measured, and deliberately
  not built, with the measurements recorded in the catalogue rows that wait on them
  rather than merely omitted. WordNet synonymy is synset co-membership: of twelve
  substitutions a writer would naturally make, five are co-members, and only four of
  eleven content words in plain prose have any synonym at all. Antonymy is thinner still
  — 6,633 lemmas have any antonym, and 2 of 11 content words in plain prose do. "Every
  substantive word replaced by a synonym" is not satisfiable by ordinary text, and a
  larger thesaurus does not change that, so `synonymic_substitution`,
  `antonymic_substitution` and `antonymic_translation` say so in their `notes`.
- The code is licensed Apache-2.0 rather than MIT, decided before the first release
  because relicensing afterwards needs every contributor's consent. What MIT does not do
  is the reason: it asks only that a notice be retained, so a fork that keeps a line in a
  file has met it while presenting the work as its own, and it is silent on trade marks,
  leaving the project's name — the one thing a fork cannot take without renaming —
  unprotected. Apache-2.0 adds a `NOTICE` every derivative distribution must carry, a
  section reserving the name, and a patent grant. The catalogue stays CC BY 4.0, and
  ADR 0006's data rule is untouched; ADR 0024 records the change. Per-file licence
  headers are deliberately not used.
- Each distribution now declares what it actually contains rather than only what its
  author wrote: `denckring` is `Apache-2.0 AND CC-BY-4.0` and ships `LICENSE-DATA` in the
  wheel, so the catalogue's attribution terms reach people who install the package and
  never see the repository; `denckring-en-data` is
  `Apache-2.0 AND CC-BY-4.0 AND BSD-2-Clause` for Open English WordNet and the CMU
  Pronouncing Dictionary; `denckring-de-data` is `Apache-2.0 AND CC0-1.0` for Wikidata
  Lexemes. Both data packages gained a `NOTICE` naming which file carries which terms and
  saying plainly that the derived lexicons are modifications of their sources.
- The core source distribution no longer carries the workspace members. It was 7.1 MB
  because it bundled `packages/` and `apps/` wholesale — the CMU dictionary, the WordNet
  glosses and the German lexicon a second time, under a licence expression that did not
  describe them and inside a package that never reads them. Excluding both leaves 0.6 MB.
  `tests/` and `docs/` stay, since a downstream packager building from source runs the
  suite. `tests/test_packaging.py` builds the sdist and reads it, because a test
  asserting that the pyproject *contains* an exclude pattern would pass while the build
  ignored it.
- A stability statement in the README, naming the four surfaces treated as contracts
  through `0.x` — procedure ids, `Report` as JSON, the catalogue export schema and the
  `denckring.lang` entry-point group — and what is expected to move: violation `rule`
  strings, `metrics` keys, message wording and `denckring.core`. The README already
  promised "stable JSON for non-Python callers" and left the scope of that promise to be
  guessed at.
- A naming policy in the README. Apache-2.0 section 6 reserves the name and says nothing
  about permitted use, so the reservation is stated as something that can be complied
  with: redistribute unmodified under the name, describe compatibility freely, rename
  before publishing a modified version.
- `denckring --version`. `__version__` was exported from the library and unreachable from
  the command line.
- `poesie_automat`, Enzensberger's Landsberger Poesieautomat: a flap-board of six lines
  by six modules by ten alternatives, so 10^36 six-line poems. `check` cuts each line
  into its six modules and asks whether every piece is one of that module's ten
  alternatives; `apply` presses the button. The count is recomputed from the shipped
  modules rather than quoted, and `Device.combinations` returns it as an integer —
  `metrics["combinations"]` is a float and cannot hold a 37-digit number exactly.
  Enzensberger died in 2022 and his word lists are in copyright until 2092, so all 360
  fillers in `data/devices/poesieautomat_2000.yaml` were written for this project; the
  mechanism is what the row catalogues, on the same footing as the substitute strips the
  `cent_mille_milliards` fixture carries for Queneau. Three design rules make *every* one
  of the 10^36 readings grammatical German rather than most of them: the article is
  folded into the noun, everything after the subject is an adjunct, and every verb is
  intransitive third person singular present. A fourth constraint is about the display
  rather than about German: the board renders letter by letter into character cells, so
  no filler exceeds eleven characters and no line the modules can assemble is wider than
  71 columns — both pinned by `test_no_flap_is_wider_than_the_board`. Two further
  constraints keep the strangeness on the right side of broken: no word reaches a line
  from two modules, compared with German inflection folded, and each family of mutually
  exclusive time anchors — when on the clock, since when, from when, how long ago, which
  month — sits in one module per line, so `Der Frost gedeiht` is possible and `um fünf
  ... um drei` is not, while roles that differ still stack.
- An optional `line` on `Slot`, with `Device.lines` and `Device.for_line`, so one device
  can hold several lines. Additive: a device file that never mentions `line` — which is
  every existing one — reads as a single line and behaves exactly as before.
- An optional `separator` on `device.segment`, defaulting to the empty string. The
  Denckring's rings concatenate with nothing between them; a board whose flaps carry
  whole words sets it to a space, and the same backtracking walk then splits a line into
  modules rather than a second segmentation being written.
- `DENCKRING_DEVICE_PATH`, a colon-separated list of directories `device.load` searches
  before the packaged one — a device's word-lists no longer have to be ours. Directories
  earlier on the path are tried first, so one can both add a new device id and shadow a
  packaged one under an existing id, which is documented as deliberate rather than left
  to be discovered. Unset, behaviour is unchanged: the packaged directory is still all
  that is searched. A directory on the path that does not exist or cannot be read is
  skipped quietly, so a stale entry does not stop a packaged device from loading. What it
  does not add: no schema versioning beyond ordinary validation, and no record of where a
  resolved device actually came from — a caller who needs to know whether a packaged
  device was shadowed must control what it puts on the path, because `load` cannot say
  so after the fact. The environment is read on every call rather than cached at import
  time, and the on-disk read `load` used to memoise by `device_id` alone is now memoised
  by the resolved path instead — a cache keyed on the id would have kept answering a
  changed environment with whatever device it saw first. A device or figure id is
  validated to a bare filename stem before it is ever joined to a directory (see Fixed,
  below), so a cartridge lives *in* a directory on the path and cannot be addressed by
  a path of its own; a relative directory on the path resolves against the process's
  working directory at call time, so changing directory after setting the variable can
  turn into silent misses under the same skip-quietly contract.
- `ConstructiveProcedure`, the template method for `apply` that `check` has always
  had: it resolves the pack, enforces both capability lists, validates parameters
  and refuses output that misrepresents what ran — identical to the input, or
  empty from input that was not — so a generator cannot forget any of it.
  `parse_apply_params` also refuses a caller-supplied `source`: the text being
  transformed *is* the source, so a second one names two texts for one argument,
  and passing both now raises `InvalidParams` instead of one silently winning.
  `ConstructiveProcedure.ignores_input` opts the three devices that never read
  their text — `denckring`, `poesie_automat`, `llull_figure` — out of the
  identity half alone, where the comparison is against an argument nothing read.
  ADR 0025.
- `Meta.apply_requires`, so a generator can declare a capability its checker does
  not need — `anagram` generates only with a word lexicon and checks with core
  alone, and one list could not say both.
- `Description.constructive` and `Summary.constructive`, reporting whether *this
  install* has a generator, distinct from `kind`, which says whether the form
  admits one. Nine rows are honestly `both` with no generator here.
- `Description.apply_params`, the generator's own JSON Schema beside the checker's
  `params`, so `denckring describe` and MCP's `describe_procedure` finally show
  `seed` and `allow_identity` — which live on `apply_params_model()` and reached no
  non-Python surface at all. Empty for a row with no generator. The two schemas
  stay separate because `source` is a checker parameter `apply` supplies for itself
  and refuses from a caller.
- `DegenerateOutput` and `InputTooShort`.
- `Production`, `Report`'s counterpart for the generating half: `procedure`, `texts`
  (best first, never empty), `truncated`, `metrics`. ADR 0026.
- `produce()` on every generator, and `denckring.produce()` at the package level,
  returning every result a generator found rather than only the first.
- `denckring.apply()` at the package level. `check` has been exported since the
  beginning and `apply` never was, so every Python caller reached through the
  registry to generate anything.
- `denckring apply --json`, emitting the `Production`, matching `describe --json`.
- `max_results` on `ApplyParams`, defaulting to 10.
- `NotConstructive`, replacing a dict literal the MCP server built by hand — one
  failure mode in this package was not a `DenckringError` and could not be caught
  with the others.
- `Candidate` and `Production.candidates`: a result carries the metrics it was ranked
  by, so an order a caller is asked to trust arrives with its reason attached.
  `anagram` is the generator that needed it — its covers carry `words` and
  `max_band`; a generator with nothing to add wraps its texts through `plain()` and
  carries empty metrics, which is every other one so far.
  `texts` is unchanged in meaning and value, now a computed field over `candidates`,
  and is still what `apply` returns and what every existing consumer reads. Both are
  named in the README's stability contract. ADR 0027.
- `Produced`, what `_produce` hands back in place of `list[str]`: its candidates, and
  whether it abandoned its own search budget. The spine can see that `max_results`
  capped a result set and cannot see that a search gave up, because giving up makes
  the set *smaller* rather than larger — `Production.truncated` is now either event.
  ADR 0026's design spec named this case in advance; `anagram`'s node budget is it.
- `lexicon.graded_words` on `LanguagePack`: every word with the SCOWL size band it
  first appears at. Separate from `lexicon.words` rather than replacing it, because
  ADR 0015's rule is one capability per question the lexicon is asked — `semordnilap`
  and `charade` ask membership and are right to keep asking the broad oracle, and a
  broad oracle is exactly what cannot rank. ADR 0028.
- `graded_words.txt.gz` in `denckring-en-data`: 77,078 words from SCOWL 2020.12.07 at
  sizes 10 through 60, one `word<TAB>size` line each, 244 KB in the wheel. 60 is
  SCOWL's own line — the largest size its documentation states it is confident holds
  no misspellings — and nothing above it ships, so `anagram`'s `max_size` is capped at
  60 rather than promising bands the data does not hold. `*-proper-names` and
  `*-abbreviations` are excluded, which is the point: they are why `known_words()`
  cannot tell `room` from `romito`. Of the 26 single letters, only `a` is kept, on
  SCOWL's bands rather than on an intuition. `scripts/build_graded_words.py` is the
  derivation, the whole of SCOWL's `Copyright` file ships as `LICENSE-SCOWL`, and the
  package's licence expression gains `HPND-sell-variant`.

- `dictionary` on `NPlus7Params`, the ordered list N+7 and S+7 displace within,
  defaulting to the pack's nouns. It sits on the **check** model rather than the
  apply model so both halves walk the same list; a generator displacing through a
  list its own checker could not see is the defect class the round-trip property
  exists to catch. The row's definition has said "the seventh noun following it in
  *a chosen dictionary*" since it was written, and until now there was no choice.
  Entries are validated as non-empty and single alphabetic words, which is ADR
  0015's rule for `nouns()` for the same reason. A supplied list is matched
  casefolded and nothing more: `pack.noun_index` lemmatises and a bare list has no
  lemmatiser behind it. `SPlus7Params` now inherits `NPlus7Params` whole instead of
  restating `offset`, so it gains the field with it. A dictionary does **not**
  unlock either row for a language whose pack has no noun list — capabilities are
  enforced before parameters are parsed — and ADR 0029 names conditional
  capabilities as what would fix that.
- `ambiguous_nouns` on the same two rows: `free` (the default, and what shipped
  before), `undecidable` or `strict`, deciding what an unchanged word that the
  dictionary lists does to the score. A word list cannot tell you that *run* is a
  verb in this sentence, so accepting the position was a policy, reported as
  `ambiguous_words` and chosen by nobody. The three names are
  `RhymeParams.unknown_rhyme`'s, which answers the same shape for a different
  undecidable. `ambiguous_words` counts the position under every reading, so the
  metric does not depend on which one was asked for. Under `undecidable`, a text
  whose every position is undecided returns an `ambiguous_nouns_undecidable`
  violation rather than scoring a vacuous 1.0 over nothing weighed.
- `allow_subset` on `AnagramParams`, accepting the transposal convention — a
  candidate built from *some* of the source's letters. Also on the check model, and
  for the same reason. It relaxes one half only: a shortfall stops being a
  violation, a surplus letter never does, since relaxing both leaves a check no text
  could fail. A candidate with no letters against a source that has some fails as
  `empty_transposal` rather than scoring 1.0 on a zero denominator. Each cover now
  carries `letters_used` in its `Candidate` metrics beside `words` and `max_band`.
  ADR 0029.
- `FrenchPack`, the third built-in default beside English and German (ADR 0022's
  shape), carrying no data files and declaring `tokens`, `alphabet`,
  `fold_diacritics` and `letter_shapes`. `œ` and `æ` fold to `oe` and `ae`
  explicitly, because neither has a casefold mapping or an NFKD decomposition the
  way `ß` does. 70 of the 119 implemented rows run in French on core alone; the
  other 49 want `syllables.heuristic` (29 rows), `phonemes` (21), `stress` (17),
  `lexicon.words` (6), `lexicon.glosses` (2) or `lexicon.nouns` (2). There is no
  `denckring[fr]` distribution, and this is not one.
- `Description.runs_in`, the languages *this install* can actually check a row in,
  computed from the packs' capabilities rather than authored. Distinct from
  `languages`, which is the row's editorial scope — `wechselsatz` is German by
  nature, not merely by capability — and the two visibly diverge on `anagram`,
  which is `languages: [en]` and runs in all three. Two fields answering two
  questions is a surface a reader can confuse; one field could not answer both.
- ADR 0029 on all of the above, and an amendment banner on ADR 0028, whose ranking
  paragraph describes three keys where `allow_subset` made four.
- German counts syllables. `GermanPack` gains `syllables.heuristic`, which it never
  had — it inherited the raising stub, so every syllabic form in the catalogue was
  unreachable in German. Vowel-group counting, always reporting itself as estimated.
  Deliberately simpler than the English heuristic rather than a port of it: a final
  "e" is pronounced in German, so the silent-e rule and the `-le` rule that exists to
  compensate for it are both dropped, and the diphthongs need no special case because
  each is already a run of adjacent vowels. It undercounts a vowel sequence spanning a
  morpheme boundary — `Museum` gives 2 where German says 3 — which a test pins rather
  than leaves to be found later. German goes from 78 of 119 runnable rows to 89.
- German runs every row. `denckring[de-wiktionary]`, a fourth distribution, vendors
  837,689 pronunciations and 179,831 glosses extracted from the German Wiktionary dump,
  giving the German pack `phonemes`, `stress`, `syllables.dictionary` and
  `lexicon.glosses`. **German goes from 89 of 119 runnable rows to 119**, and
  `denckring eval --all` from 365 passing cases to 401. Syllable counts and stress are
  read off the transcription rather than sourced separately, so `stress` can never be
  present without `phonemes`. Measured 94.0% token coverage over 340,958 tokens of
  Wieland, Goethe, Kafka and Mann; the residue is pre-1901 orthography and proper names.
  ADR 0030.
- `denckring-de-data` gains a `pack()` factory, and the `de` entry point resolves to it
  rather than to a class. Core refuses two packs claiming one language and ADR 0013
  forbids merging CC BY-SA data into a CC0 distribution; a factory satisfies both, and
  every pack's `capabilities` stays a fixed `ClassVar` rather than becoming computed.
- 36 German golden cases across 30 rows, including Goethe's opening hexameter from
  *Hermann und Dorothea*, Voß's from the *Odüssee* and Heine's trochaic tetrameter,
  which scan under the checkers unmodified.
- `proteus_verse`, the 120th implemented procedure and the 28th generator. A line whose
  words permute into many metrically valid variants: `check` asks that the line scans as
  written *and* that its words admit at least `minimum` orderings that also scan,
  scored separately because a writer can fix them separately. `produce` returns the
  orderings. Voß's opening hexameter admits 1,728 of its 40,320.
  No new prosody abstraction: the scansion is `core.prosody`'s, and the handover that
  proposed a `Meter`/`Syllabifier` pair was answered by what already existed — a pack's
  `stress_patterns` already returns every reading a word has, which is the ambiguity
  that proposal existed to model. The factorial is guarded by counting rather than
  enumerating: a walk over (words placed, syllables filled) is bounded by 2^n where
  scanning each ordering is n! * 32, and lines above `max_words` are refused rather
  than searched.
- `InputTooLong` takes the noun it counted. It said "letters" unconditionally, which is
  right for `anagram` and wrong for a row that rearranges words.
- A device is an address space. `Device.at` and `Device.address` are the two directions
  of its index — Piṅgala's *naṣṭa* and *uddiṣṭa*, which makes the odometer reading an
  attested procedure rather than a modern gloss — over the mixed base `Device.radix`.
  The first slot is the most significant digit, stated as a choice because sources
  differ. `Abbildung` is reading 52,699 of Harsdörffer's 103,680,000.
- `Device.mask` records which readings are attested, after al-Khalīl's *muhmal* marking:
  enumerate the space, then flag which members are real. `hold` is the default because
  it is what the source does. `denckring apply` reads it under `attestation: mask`, and
  refuses in both directions — a device with no mask, or a pack that cannot answer.
  Measured: 0 of 20,000 spins of the rings is a word the German lexicon knows, while
  4.40% of German nouns are spellable on them.
- `denckring` spins `max_results` times rather than once, because a generator that flags
  which of its own outputs are real needs more than one to flag.
- `Device.disputed_totals` carries the counts the literature asserts that the inventory
  does not support, with who asserts each. `combinations` stays computed. ADR 0031.
- `hemeling`, the 155th catalogued row and the 121st implemented. Johann Hemeling's
  *Arithmetische Letter- oder BuchstabWechslung* (1653) asks for an anagram of a name
  *und durch Reime zu erklähren* — explicated beneath it in rhymed verse — and both
  halves are mechanically checkable, which is what makes it the tightest rule in the
  surveyed European material. The first line is judged by `anagram`'s multiset
  comparison and the rest by `rhyme_scheme`'s scheme walk, imported rather than
  reimplemented, so a text this row accepts is one those two accept. The halves are
  scored separately, so a broken rhyme over a sound anagram reads 0.5 and says which.
  The primary text has not been consulted; Kilcher, who read it, is named in the source.
- `docs/expansion_ideas/` is excluded from the source distribution, on the argument the
  existing exclusions already make: those are working documents — proposals, handovers
  and research notes addressed to whoever picks the work up — not documentation of what
  this package does. They stay in git, because the ADRs cite them.
- The sdist bound is raised from 1,000,000 to 1,200,000 bytes, by maintainer decision
  after chapter 4 crossed the old one for real. A side effect worth naming: the whole
  suite now passes on a working tree, where `test_the_sdist_stays_small` had failed
  locally and passed in CI for as long as the bound existed — the untracked 68 KB blob
  the local build swallows no longer pushes the archive over. The new number is a stated
  trade: 236,778 bytes of prose headroom against roughly 13,000 bytes of margin on the
  other side, which is what still lets the bound catch the smallest vendored data file
  being re-included. There is no per-file bound that separates the two, because
  `uv.lock` is larger than `graded_words.txt.gz`.
- `docs/expansion_ideas/` is now kept out of the sdist by a name-based test as well as by
  the size bound, since a raised bound would let a silent re-inclusion fit underneath it.

### Changed

- Twenty-five fillers in `data/devices/poesieautomat_2000.yaml` — published data, CC
  BY 4.0 — replaced, because assembled they read as camp and confinement imagery.
  Twenty-four were of that family: `der Zaun`, `am Zaun`, `Die Mauer`, `Die Sperre`,
  `auf Posten`, `die Wache`, `die Rampe`, `das Gleis`, `Das Lager`, `im Lager`,
  `im Graben`, `im Moor`, `in Ketten`, `in Trümmern`, `in Flammen`, `unter Zwang`,
  `aus Draht`, `mit Draht` and `Der Draht`, plus `Das Gitter` (*hinter Gittern*),
  `in Deckung`, `die Kammer`, `die Sirene` and `brennt`, the last five found by
  sweeping rather than listed. Each is innocent read alone — a loading ramp, a
  warehouse, a railway track, a watch, a fence — and the defect was never one flap
  but what a board of 10^36 readings eventually sets beside what. That is countable
  exactly rather than by sampling, because a line is six modules of ten and the
  per-module counts convolve: of the 6,000,000 lines the board can assemble,
  1,633,120 (27.2%) carried at least one of these words and 244,620 (4.08%) carried
  two or more, which put 22.686% of all 10^36 poems — better than one poem in five —
  on the wrong side of it. Over the replaced file both figures are 0. Nobody can read
  10^36 combinations, so the guard is to keep the material out of the modules rather
  than to look for it in the output, and the device header now carries that as a
  seventh constraint, marked as resting on judgement rather than on a test — as, it
  also now records, the fourth rule already did, there being no test in this
  repository for the ADV prohibition either.
- The twenty-fifth, `ohne Zeugen`, went on a neighbouring ground: beside `Die
  Anzeige`, which is a notice and a display and also a criminal complaint, it read as
  a denunciation, in 1.00% of that line's 1,000,000 readings — 10,000 of them. It is
  now `ohne Strom`. Everything about the machine is unchanged: every module still
  holds ten alternatives, `Device.combinations` is still exactly 10^36, no filler
  exceeds eleven characters, no line's assembled width rose, all 360 stay distinct
  case-folded, and the six schemas, the three grammaticality rules and the ADV rule
  are untouched. `kippt`, which replaced `brennt`, is the only one of the thirty
  verbs that is ambitransitive; rule 3 holds for all 10^36 readings anyway, because
  no schema offers a verb an object, and the header records the exception. The second
  positive golden fixture spun four of the replaced flaps and was rewritten to the
  same seed's new reading, which leaves both properties its `source` claims —
  disjointness from the first fixture and no repeated word stem — true and re-derived
  on every run.
- **Breaking:** `seed` is a parameter on `SeedParams` rather than a keyword in the
  `Constructive.apply` signature, carried only by the ten procedures that draw at
  random. A keyword named in the signature bound before `**params`, so `seed` was
  never validated and all 27 generators accepted `seed="not-an-int"`. Passing
  `seed` to a procedure that does not draw now raises `InvalidParams` instead of
  being silently ignored. `lang` remains a reserved keyword on the same signature
  for the same reason — no params field may be named `lang` either, and
  `ApplyParams` now says so.
- **Breaking:** `spoonerism` raises `InputTooShort` rather than `NoCandidateWord`
  for a text of fewer than two words, and `ideenwuerfeln` raises it rather than
  `MalformedCorpus` for a corpus holding fewer entries than a throw needs. Both
  were the shape `recombination` already raised `InputTooShort` for, so the code a
  caller retries on depended on which procedure they had called. `NoCandidateWord`
  keeps its narrower meaning — enough units, none of them suitable — and
  `MalformedCorpus` keeps `corpus.parse`'s: unreadable, not merely small.
  `InputTooShort`'s message now ends on a remedy, as the other errors do, and
  counts its units in English rather than reading "0 line".
- **Breaking:** `ConstructiveProcedure.apply_params_model()` is abstract. It used
  to synthesise the checker's model widened by `ApplyParams`; all 27 generators
  declare their own, so the default had no caller and carried an MRO trap.
- `boustrophedon`, `cent_mille_milliards`, `recombination` and `wechselsatz` raise
  `InputTooShort` where they used to return their input unchanged. `wechselsatz`
  raises it twice over: once for a frame offering no choice at all, and once for
  a frame whose alternatives the tokenizer used to check the result cannot read
  back as single words — a gap `_apply`'s `drawable` filter now closes by simply
  never drawing such an alternative, which is itself a known, accepted cost
  documented in the code and deferred to chapter 2.
- `apply_procedure` (MCP) returns `texts` and `truncated` alongside `text`. Additive:
  `text` keeps its meaning and value as the first of `texts`.
- `paragram` returns every candidate it scores, best first, where it scored them all
  and returned one. `apply`'s result is unchanged.
- `apply_procedure` (MCP)'s `message` for a non-constructive procedure, from a
  hand-built sentence to `NotConstructive`'s own wording, which additionally points a
  caller at `constructive` in `describe_procedure`. `code` and `detail` are unchanged.
- **Breaking for anyone who has written a generator:** `_produce` returns `Produced`
  rather than `list[str]`. All 27 generators moved with it; `denckring.core` was
  already outside the stability statement, and this is what that clause is for.
- **Breaking:** the identity guard compares casefolded text, so output differing from
  its input only in capitalisation is refused. `word_ladder.apply("Cat",
  target="cat")` now raises `DegenerateOutput.IDENTICAL` where it returned `"cat"`.
  `apply("cat", target="cat")` already raised, so the change makes that row
  consistent with itself rather than taking anything away.

- `get_pack("fr")` returns a pack instead of raising. **Breaking for anyone catching
  `UnknownLanguage` on `"fr"`:** `check(..., lang="fr")` on a row needing only core
  capabilities now runs, and on a row needing a lexicon it raises `MissingCapability`
  naming the capability rather than `UnknownLanguage` naming the language. `Lang` has
  been `Literal["en", "de", "fr"]` since the first release and every catalogue row
  carries a French name and definition, so the old error pointed at
  `denckring[fr]` — a distribution that does not exist and was never planned. The
  failure moves to the right layer; it does not go away.
- `MissingCapability`'s remedy is conditional on a data distribution existing.
  It interpolated the language into `pip install denckring[{lang}]`, which was
  harmless while every language reaching it had a package and became a false promise
  the moment French did not: the 49 rows a French caller cannot run were each
  pointing at `denckring[fr]`, which does not exist. English and German keep the
  install hint; anything else now reads "No data distribution supplies it for 'fr'".
  The `code` (`missing_capability`) and `detail` are unchanged, so a caller matching
  on either is unaffected; one matching on `message` text for a language with no
  extra is not. Untouched and older than this: naming a language's extra still
  assumes that extra supplies the capability, and `denckring[de]` carries no `stress`.
- `anagram` ranks covers by `letters_used` descending before ADR 0028's three keys,
  because under `allow_subset` every single word that fits the source is a valid
  transposal — 373 of them for `astronomer` — and word count first would bury every
  cover worth reading. With the flag off the new key is constant across covers and
  the order is byte-identical to ADR 0028's, held by a regression test rather than
  by the argument. The flag costs no search: `astronomer` visits 747,769 nodes
  either way, because a cover is recorded at nodes the walk already visits. What it
  multiplies is results — `astronomer` 1,421 covers to 15,185, `dormitory` 48 to 742,
  one fewer out of `produce` in each case, which drops the identity cover — which
  makes `Production.truncated` true on nearly every subset call against the default
  `max_results` of 10. That field has meant both "the search abandoned its budget"
  and "`max_results` capped the list" since it existed; `allow_subset` makes the
  second the common case, and a caller still cannot tell them apart.
- `tests/test_round_trip.py` draws blank-line paragraphs and terminated sentences
  by construction instead of waiting for a flat draw to offer them, and
  `max_examples` falls from 1,000 to 600. The old budget was never measured: over
  twelve fixed seeds the flat-only strategy reached every constructive row on 3 of
  12, missing `recombination` on nine and `every_nth_word` on three. The new
  composition reaches every reachable row on 60 of 60 replayed seeds at 300
  examples, and 600 is twice that floor. The cost is a narrower flat draw —
  `st.one_of` dedupes branches by identity and does not sample them uniformly,
  measured at about 20% for a flat branch against 45% for the prose one — which
  starves `spoonerism`, the row that wants flat text and the first to go missing
  when the budget is cut.

### Fixed

- `assonance_constraint` and `spoonerism` identified a vowel phoneme by CMUdict's stress
  digit — a convention no other source uses. Both rows declare only `phonemes`, so the
  moment German had phonemes they ran in German and found no vowels in any German word:
  `assonance_constraint` failed every German text and `spoonerism` read every word as
  pure onset. `LanguagePack.is_vowel_phoneme` puts the question on the pack, where the
  answer lives.
- `denckring-en-data` declared the `syllables` capability and never implemented it, so
  `get_pack("en").syllables("table")` raised `MissingCapability` naming a capability the
  pack declared. No row requires it, so nothing was broken; but `runs_in` computes from
  `capabilities`, so the first row to require it would have been reported as running in
  `en` and would then have raised. The claim is removed: a pronouncing dictionary is not
  a hyphenation dictionary.
- `device.load` and `device.load_figure` built a filename by interpolating the caller's
  id directly — `directory / f"{item_id}.yaml"` — which `Path` does not make safe:
  `Path.__truediv__` silently discards the left operand when the right is absolute, and
  a `..` segment is never rejected. An id of `/etc/passwd` or `../../etc/passwd` read
  that file and returned it as though it were a device. This predates
  `DENCKRING_DEVICE_PATH` — the same interpolation was already present for both loaders
  when they only ever read the packaged directory — but the cartridge is what turns a
  latent gap into a routine one: it multiplies the directories an id can escape from and
  documents "point this at your own files" as a supported feature. It is reachable from
  outside the process, not only from Python: `DeviceParams.device` is a bare `str`, an
  MCP client supplies it directly via `mcp/server.py`'s `**(params or {})`, and the CLI
  reaches it through `--param device=...`. Both loaders now validate an id as a bare
  filename stem — no separators, no `..`, never absolute — through one shared helper,
  and independently confirm the resolved path is inside the directory it was joined to,
  so the rule and the filesystem agree. An id that fails either check is treated exactly
  as an id no directory offers: `UnknownDevice`/`UnknownFigure`, not a different error.
- A cartridge file that failed to parse as YAML, or parsed but did not fit the `Device`/
  `Figure` schema, let the raw `yaml.YAMLError` or Pydantic `ValidationError` escape.
  Both exceptions quote content from the file in their default message — a YAML parse
  error echoes a snippet of the source around the failure, and a Pydantic error echoes
  each offending value back — which is a content-disclosure path once a cartridge is by
  design arbitrary user-authored YAML, and it broke the contract `mcp/server.py` states
  in its own docstring: only a `DenckringError` is ever converted to data for a model to
  act on. Both loaders now raise `MalformedDevice`/`MalformedFigure` — new
  `DenckringError` subclasses alongside `MalformedTable` and `MalformedCorpus` — naming
  the path and a short, content-free reason (an exception's class name, or a count of
  validation errors) instead.
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
- The English lexicon is now derived from Open English WordNet 2024 rather than Princeton
  WordNet 3.1, which is unmaintained. The noun list grows from 55,239 to 56,468 entries
  and 78,865 glosses arrive with it; `LICENSE-WORDNET` is replaced with the CC BY 4.0
  notice OEWN carries, and the data package's README stops naming the old release.
  **This changes published output:** `n_plus_7` and `s_plus_7` both count forward through
  that list, so a displacement that landed on one word can now land on another — *cat*
  displaces to *catacomb*, where it displaced to *catafalque* before. N+7's golden
  fixture, strategy and tests are updated to the new list; S+7's fixture words were not
  affected, but the same shift applies to any input.
- Four catalogue rows named capabilities they never needed, each corrected against what
  the row actually does: `kangaroo_word` needs a word list (`lexicon.words`), not a
  thesaurus, since whether two words are synonyms is the writer's claim; `chimera`
  substitutes by part of speech and is blocked on `pos` alongside `homosyntaxism` and
  `verbless_prose`; `definitional_translation` needs glosses *in the target language*
  (`lexicon.glosses.bilingual`), which English ones do not serve and no shipped pack
  provides, named the way `homophonic_translation`'s `phonemes.bilingual` already is.
- `glosses`' inflection fallback tried stripping `ed` and `ing`, which resolved *cared* to
  *car* and *poled* to *pol* — unrelated headwords, returned with the confidence of a
  real answer, and enough to make the definitional rows demand the wrong sense of a
  correctly expanded word. Measured over a sample sentence, `s`/`es` stripping earns its
  place and `ed`/`ing` bought two extra resolutions of which both were wrong, so only
  `s`/`es` is kept. The docstring no longer claims resolution never guesses: it is
  best-effort, and only the empty sequence is a guarantee.
- The three distributions are version-locked to each other. `denckring-en-data`
  subclasses the core English pack, and `release.yml` publishes all three from one
  workflow for exactly that reason, but each declared a bare `denckring` dependency and
  each extra a bare data-package one — so `pip install denckring-en-data` was free to
  pair a subclass with a core it was never built against. All four declarations now pin
  `==0.1.0`; `[tool.uv.sources]` keeps local development on the workspace copies.
- `project.urls` gained Documentation and Changelog entries, which are what PyPI's
  sidebar shows.
- `cent_mille_milliards` silently dropped a sheet line offering no alternatives,
  drawing one fewer line than the sheet has positions — the shape its own
  `missing_line` violation exists to catch. `apply('a|a\n|')` returned one line
  where `check` required two. It now raises `InputTooShort` for a sheet with an
  empty position rather than drawing from it.
- `recombination` shuffled an unterminated trailing fragment into the draw, where
  `" ".join` could merge it with its new neighbour and re-split into a different
  multiset than the one shuffled — exactly what `check` compares against. It now
  pins the tail out of the shuffle and permutes only the terminated sentences.
  Both were made reachable by the previous chapter's wider round-trip input
  alphabet and surfaced only intermittently, because
  `tests/test_round_trip.py::test_apply_output_satisfies_check` is not
  derandomized.
- `apply anagram "astronomer"` raised `DegenerateOutput`, and `dormitory` with it.
  The generator walked `pack.nouns()` greedily — a source word that is itself a noun
  is the longest cover of its own letters — and emitted whatever letters it could not
  spend as a run of single letters, which kept `check` satisfied and said nothing.
  It now searches the graded lexicon depth-first for sets of words whose letters are
  exactly the source's, bounded by `max_words`, `min_word_length`, `max_size` and a
  budget of 1,000,000 nodes, and ranks what it finds by fewest words, then by the
  SCOWL band of the cover's least common word, then alphabetically. `dormitory` gives
  `dirty room`, one of 47 covers; `astronomer` gives `arrest moon`, one of 1,420. A
  walk that cannot spend its remaining letters is not a cover and is abandoned rather
  than padded. The catalogue row declares `lexicon.graded_words` under
  `apply_requires` and not `requires`, since `check` has always run on core alone.
- The identity guard compared `produced.strip() == text.strip()`, so a generator whose
  output is casefolded never compared equal to a capitalised input and slipped it:
  `apply anagram "Dormitory"` returned `dormitory`, the reported defect still live for
  anyone who types a word the way people write one. Fixed at the spine rather than in
  `anagram`, because the rule is the spine's and belongs in one place. See **Changed**
  for the one existing result this moves.

[Unreleased]: https://github.com/senzelden/denckring/commits/main
