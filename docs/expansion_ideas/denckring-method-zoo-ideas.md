# denckring — Idea Package: Expanding the Method Zoo

**Status: advisory, not a specification.** This document was written without sight of the
current codebase. The implementation is further along than the author of this document knows.
Nothing here should be treated as an instruction to refactor, rename, or restructure existing
work.

**How to use this file.** Read the existing code first. Then treat each section below as a
menu of candidates and design pressures. For every item, the useful question is: *does this
already exist under another name, does it fit the existing abstractions, or does it argue for
a new one?* Where an idea here conflicts with a decision already made in the repo, assume the
repo is right and note the conflict rather than acting on it.

**Primary goal of this package:** breadth of the method zoo, plus the validation properties
that make breadth safe to add.

---

## 1. Framing: primitives before procedures

The corpus of documented writing procedures is large (target: 500+), but the *algorithms* are
few. Most procedures decompose into a small set of operations applied at a chosen granularity.

| Primitive | Operation | Example procedures |
|---|---|---|
| **Substitute** | replace units under an equivalence relation | S+7, chimère, homosyntaxism, homoconsonantism, homophonic translation |
| **Filter** | accept units satisfying a lexical predicate | lipogram, univocalic, snowball, prisoner's constraint |
| **Permute** | reorder units by a fixed or computed permutation | sestina/quenine, Mathews' Algorithm, Tape Mark I, cut-up |
| **Expand** | replace a unit with a slot-filling or a definition | Denckring, Queneau, littérature définitionnelle, larding |
| **Contract** | select a subsequence of the source | erasure, haikuization, blackout, found text |
| **Interleave** | merge two or more sources under a schedule | perverbs, fold-in, chimère (source side), cento |

Granularity axis: grapheme → phoneme → syllable → morpheme → word → line → sentence →
paragraph → section.

**The design claim worth testing against the existing code:** a procedure is best modelled as
`(primitive, granularity, resource, parameters)` rather than as a bespoke function. If the
current architecture already does something equivalent, ignore this section. If it is 40
hand-written functions, the cross-product view is where the next 400 come from cheaply — and
it makes combinations (lipogrammatic S+7, erasure-then-snowball) fall out for free instead of
needing 400 more functions.

**Second claim:** the split the author maintains between *Verfahren* (generative procedures)
and *Strukturen* (text forms/architectures) should survive into the type system as two
composable types, not one. `apply(procedure, form)` is a more useful API than a flat registry,
and it is the reason a sestina can be both a form (six stanzas, envoi) and a procedure (the
spiral permutation).

---

## 2. Zoo expansion candidates

Each entry: name — definition — programmability note. `[V]` marks a cheap exact validator,
`[S]` marks generation-requires-search, `[M]` marks model-dependent (no exact validator).

### 2.1 Grapheme and letter constraints

Mostly `[V]` validators, mostly `[S]` generators. High yield, low implementation cost.

- **Lipogram** — exclude a letter set. `[V]` trivial. `[S]` generation; prefix-decidable, so
  logit-maskable.
- **Univocalic / monovocalism** — exactly one vowel permitted. `[V]`.
- **Pangram** — contains every letter. `[V]`. **Perfect pangram** — each letter exactly once;
  `[S]` and genuinely hard, a good stress test for the search layer.
- **Heterogram** — no letter repeats (cf. Perec's 11-letter *Alphabets*). `[V]`.
- **Tautogram** — every word begins with the same letter. `[V]`.
- **Acrostic / mesostic / telestich** — encoded string at line-initial / medial / final
  position. `[V]`. Mesostic needs the Cage spelling rule as a parameter (100%/50% mesostic).
- **Abecedarian** — units ordered by initial letter through the alphabet. `[V]`.
- **Beau présent / belle absente** — use only (resp. avoid) the letters of a dedicatee's name.
  `[V]`; parameterised lipogram, so it should reuse the same predicate.
- **Prisoner's constraint** (*contrainte du prisonnier*) — no ascenders or descenders.
  `[V]`; needs a per-script glyph-class table, which is a reusable resource for other
  typographic constraints.
- **Palindrome** — at grapheme, word, line, or verse granularity. `[V]`. Worth implementing
  generically over granularity rather than as three procedures.
- **Semordnilap / reversible pairs** — word reverses to another word. `[V]` with a lexicon.
- **Anagram / heterogrammatic transposition** — `[V]` by multiset equality; `[S]` generation.
  Not prefix-decidable — good illustrative case for the constraint taxonomy in §3.
- **Snowball / melting snowball / rhopalic** — monotone word or syllable length. `[V]`,
  prefix-decidable, maskable.
- **Chronogram** — letters read as numerals sum to a target year. `[V]`. Latin/Roman numerals;
  see also abjad (§2.7) and gematria (§2.7) for the same primitive in other scripts.
- **Slenderizing / letter-shift / epenthesis** — remove, shift, or insert a letter throughout
  and re-read. `[V]` reversible → round-trip test.
- **Cipher-as-constraint** — text that also satisfies a transposition or substitution scheme.
  `[V]`; cheap and unusual.

### 2.2 Lexical substitution under an equivalence relation

The richest family, and the one that most rewards a shared resource layer.

- **S+7 / N+7 and M±n variants** — replace each noun by the n-th following noun in a reference
  dictionary. `[V]` exact given the same dictionary; reversible → round-trip test. The
  dictionary itself must be a declared, versioned resource or results are irreproducible.
- **Chimère (chimera)** — strip nouns/verbs/adjectives from a source, refill from three other
  texts. `[V]` by POS-skeleton equality against the source.
- **Homosyntaxism** — preserve the POS sequence, replace all content. `[V]` by tag-sequence
  equality.
- **Homoconsonantism / homovocalism** — preserve the consonant (resp. vowel) skeleton. `[V]`
  exact, script-dependent.
- **Homophonic translation** — preserve sound, discard meaning (Van Rooten, Zukofsky). `[M]`
  exact validation impossible; scoreable by phoneme-string edit distance, which is a decent
  proxy and testable as a *metric*, not a predicate.
- **Antonymic translation** — replace each unit by its opposite. `[M]`, needs an antonym
  resource; WordNet for English, OdeNet for German.
- **Littérature définitionnelle** — replace each content word by its dictionary definition,
  iteratively. `[V]` weakly (expansion factor, resource membership); the interesting testable
  property is monotone growth and fixed-point behaviour under iteration.
- **Larding / line-stretching** — insert new sentences between two fixed poles, recursively.
  Structural `[V]`: first and last sentence preserved, insertion depth respected.
- **Perverb** — cross two proverbs at their pivot. `[V]` given a proverb corpus.
- **Roussel's procédé** — build a text between two near-homophonic sentences. `[M]`; the
  endpoint constraint is `[V]`.
- **Translation relay / back-translation chain** — round-trip through n languages. `[M]`;
  measurable as semantic drift per hop, which makes a nice built-in experiment.
- **Register transposition** (*Exercices de style*) — `[M]`, LLM-dependent; worth including
  precisely because it forces the API to admit model-backed procedures alongside deterministic
  ones.

### 2.3 Permutation

- **Sestina and the generalized n-ine (quenine)** — the spiral end-word permutation. This is
  the mathematically richest item in the zoo: it only closes for *Queneau numbers*, so the
  library can expose `admissible_n()` and property-test that the permutation has full order
  exactly for those n. Strong, self-contained test target; also a good doctest showcase.
- **Mathews' Algorithm** — matrix rotation over text elements. Deterministic, `[V]`.
- **Tape Mark I rules** — Balestrini's four recombination rules, published with the poem in
  *Almanacco Letterario Bompiani* 1962. See §3 on using this as a golden fixture.
- **Cut-up / fold-in** — Gysin/Burroughs. `[V]` as a multiset-preservation check at the chosen
  granularity.
- **Pantoum / villanelle / terza rima / ghazal refrain schedules** — arguably *Strukturen*, but
  each is a deterministic line-scheduling function and should probably live as one.
- **Su Hui's 璇璣圖 (Xuanji Tu)** — 29×29 character grid readable in many directions, yielding
  thousands of poems. Effectively a two-dimensional addressable combinatorial machine and a
  spectacular test case for the index-bijection idea in §3. *Verify grid dimensions and reading
  rules against a scholarly source before encoding.*

### 2.4 Slot grammars and historical combinatorial machines

This is the family the package is named after, and the one where addressable indexing
(§3) applies directly.

- **Harsdörffer, *Fünffacher Denckring der Teutschen Sprache*** (1651) — five concentric rings
  (prefixes, initial letters, medial letters, endings, suffixes). The actual ring contents are
  printed in the *Delitiae Mathematicae et Physicae*; encoding them as shipped data would be a
  genuine scholarly contribution and an obvious signature feature for a package with this name.
- **Llull, *Ars combinatoria*** — volvelles over the principia B–K. Well documented, directly
  encodable as a figure-and-wheel data structure.
- **Kircher, *Arca Musarithmica*** — tabular slats; the musical version of the same idea, with
  a documented syllable-count-to-slat mapping.
- **Jean Paul, "Ideenwürfeln"** (SBB Berlin, Nachl. Jean Paul, Fasz. IX, Konv. 7, Feb 1795) —
  once transcribed, becomes a concrete dice-driven generator with a documented provenance. This
  is the item most likely to be *only* in this package.
- **Queneau, *Cent mille milliards de poèmes*** — 10 sonnets × 14 lines; 10¹⁴. Public-domain
  status: **not** public domain, ship the mechanism and a substitute corpus.
- **Enzensberger, Landsberger Poesieautomat** — 6 lines × 6 slots × 10 fillers = 10³⁶. The
  grammar is recoverable by aligning the published stanzas; the *lexicon* is Enzensberger's and
  under copyright, so ship the schema with an original filler set.
- **Knowles & Tenney, *A House of Dust*** (1967) — four-slot quatrain grammar (material /
  location / light source / inhabitants), FORTRAN original. Small, historically attested,
  perfect smoke-test grammar.
- **Strachey, *loveletters*** (1952, Ferranti Mark I) — template with adjective/noun/adverb
  slots and a salutation schedule; reconstructed by David Link. Oldest known machine text
  generator; excellent as the "hello world" of the historical suite.
- **Tzara's hat** — words drawn at random from a source. Trivial, but the historical anchor for
  the Contract/Permute primitives.
- **Tracery-style recursive grammars** — the modern generalization; worth supporting as an
  import/export format so users can bring existing grammars.

### 2.5 Stochastic and statistical

- **Shannon's approximations to English** (1948) — order-0 to order-2 letter and word
  approximations, with the published sample outputs. Canonical fixture material.
- **Theo Lutz, *Stochastische Texte*** (1959, Zuse Z22) — lexicon drawn from Kafka's *Schloss*
  plus logical connectives, probabilistic rather than uniform. Algorithm and outputs published
  in *augenblick*. Note the copyright status of the Kafka-derived lexicon is fine (Kafka d.
  1924) but Lutz's own text is not; reimplement the algorithm, cite the outputs, don't ship them
  as content.
- **Markov / n-gram at char, syllable, and word granularity** — the baseline against which
  every fancier method should be benchmarked.
- **Travesty algorithm** (Kenner & O'Rourke, 1984) and **Dissociated Press** (Emacs) — two
  documented, subtly different n-gram variants. Differential testing between them is a nice
  demonstration that the library distinguishes procedures that look identical in prose
  description.

### 2.6 Erasure, contraction, and conceptual procedures

- **Erasure / blackout** — output must be a *subsequence* of the source. This is the single
  cleanest validator in the whole zoo (`is_subsequence`), and it generalizes: haikuization,
  found poetry, cento (with multi-source subsequence), and Montfort's *The Deletionist* all
  reduce to constrained subsequence selection. Strongly recommend it as a first-class primitive
  if it isn't already.
- **Cento** — every line taken verbatim from another author. `[V]` by line-level membership
  against a declared corpus.
- **Uncreative writing** (Goldsmith: transcription, retyping, appropriation) — `[V]` by
  identity or near-identity; interesting mainly as the degenerate case that tests whether the
  API can express "the procedure is the framing".
- **Computational conceptualism** (Bajohr's *Halbzeug*, *Naturtheater*) — corpus-scale
  operations over found digital text; belongs in the zoo as the contemporary German-language
  anchor the collection explicitly wants.
- **ppg256 / Taroko Gorge and its remix family** (Montfort) — tiny generators whose *remixability*
  is the point. A "remix" affordance (swap the wordlists, keep the schedule) maps directly onto
  the cartridge idea and is a cheap, very demo-able feature.

### 2.7 Non-European traditions

The collection explicitly wants more of these, and they are badly under-served by existing
libraries — this is where the package can be distinctive rather than redundant. Most are
*more* formally strict than the Oulipo material, hence highly validatable. **Every item here
should be verified against a scholarly source before encoding; the descriptions below are
sketches, not authorities.**

**Sanskrit / Tamil (citrakāvya, "picture poetry")**
- **Niroṣṭhya** — verse avoiding all labial consonants. A lipogram over a *phonological* class
  rather than a graphemic one; argues for the phoneme granularity being real.
- **Ekākṣara** — verse using a single consonant throughout.
- **Anuloma-viloma / vilomakāvya** — verse readable forwards and backwards. The
  *Rāmakṛṣṇavilomakāvyam* reads as the Rāma story forwards and the Kṛṣṇa story backwards — a
  dual-text palindrome, and the most demanding generation target in the entire zoo.
- **Bandha** (gomūtrikā, cakra-bandha, etc.) — verses laid out on a grid or figure such that
  reading paths coincide. Two-dimensional constraint; shares machinery with Su Hui (§2.3).
- **Chandas** — quantitative metre by light/heavy syllable (laghu/guru) patterns. Fully
  algorithmic `[V]`; the gaṇa system is a direct binary encoding and one of the best-documented
  metrical systems anywhere.

**Chinese**
- **Lüshi / jintishi tonal patterns** (平仄) — level/oblique tone schemes with fixed positions.
  `[V]` exact given a tone dictionary; Unihan or a Middle-Chinese rime table for historical
  tones.
- **Duìzhàng (parallelism)** — paired lines matching in POS and semantic category. `[V]` for the
  syntactic half, `[M]` for the semantic half.
- **Huíwén shī (回文詩)** — palindromic and multidirectional verse (see Su Hui).
- **Cángtóushī (藏頭詩)** — acrostic.

**Arabic / Persian / Turkish**
- **Ghazal** — qāfiya (rhyme) plus radīf (repeated tail word). `[V]` exact.
- **Luzūm mā lā yalzam** (al-Maʿarrī) — self-imposed double-consonant rhyme beyond requirement.
  `[V]`.
- **Abjad chronogram (tārīkh)** — hemistich whose letters sum to a date. `[V]`, same primitive
  as the Latin chronogram — good evidence for the cross-cultural primitive claim.
- **Tawriya / īhām** — deliberate double meaning. `[M]`.
- **Muwashshaḥ** — strophic form with kharja envoi.

**Hebrew**
- **Tzeruf** (Abulafia) — systematic letter permutation as a compositional and meditative
  technique; 13th century, contemporaneous with Llull, and mechanically identical to a
  permutation engine.
- **Gematria-constrained composition** — numeric-sum targets. `[V]`.
- **Piyyut acrostics** — alphabetic and name acrostics. `[V]`.

**Japanese**
- **Renga / haikai linking rules** — tsukeai (link-and-shift), plus per-position requirements
  for kigo (season word), kireji (cutting word), and prohibitions on returning to an earlier
  topic within n verses. This is a *sequence constraint over a collaborative chain* and does not
  fit the single-text model — worth checking whether the current API can express it at all.
- **Honkadori** — allusive variation on a known poem; `[V]` as an n-gram overlap floor against a
  declared source poem.
- **Kakekotoba** — pivot word carrying two readings; a homophonic slot.
- **Engo** — conventional word-association networks; a graph resource, reusable for other
  association-driven procedures.

**Celtic and Germanic**
- **Cynghanedd** (Welsh) — strict consonantal harmony patterns within the line. Formalizable,
  and prior art exists for automated checkers.
- **Dróttkvætt** (Old Norse) — syllable count plus internal rhyme (skothending/aðalhending) plus
  alliteration at fixed positions. `[V]`.
- **Kenning formation** — productive compound generation by a documented rule; a *generator*,
  not just a constraint, and unusually well suited to a slot grammar.
- **Sievers' five types** (Old English) — half-line stress patterns. `[V]` given a stress
  lexicon; contested among metrists, so expose the ruleset as a parameter.
- **Dán díreach / rannaigheacht** (Irish) — syllable, rhyme, and alliteration constraints.

**Other**
- **Pantun** (Malay) — the ancestor of the pantoum; quatrain with pembayang/maksud halves.
- **Qenē** (Ethiopian, *sem-enna-werq*, "wax and gold") — two simultaneous readings, surface and
  hidden. `[M]`, but the two-layer structure is a useful abstraction that also covers tawriya
  and kakekotoba.

---

## 3. Validation ideas

### 3.1 Constraint taxonomy: prefix-decidability

Worth encoding explicitly on each constraint, because it determines what can be *enforced*
rather than merely *checked*:

- **Prefix-decidable** — judgeable on a partial string (character-set exclusion, monotone
  length, syllable budget, rhyme position, ordered-alphabet). These compile to logit masks and
  can be enforced exactly during decoding.
- **Suffix-completable** — a partial string may still be extended into a valid one but isn't
  itself valid (pangram, chronogram sum).
- **Whole-text only** — anagram, palindrome-with-unknown-length, total letter counts. These need
  search or rejection sampling.

Suggested consequence: a constraint exposes `check(text)` always, and `mask(prefix, vocab)`
optionally. Two compilation targets from one declaration. This also connects to the separate
logprob harness: masking needs logits, and per-token surprisal gives a selection signal for the
Balestrini move (generate many, keep few).

### 3.2 Historical golden files

Several procedures have published algorithms *and* published outputs. Reproducing attested
output from a reimplemented procedure is a much sharper test than "it runs", and is a research
contribution in its own right:

- Strachey, *loveletters* (1952) — via Link's reconstruction and emulator.
- Shannon (1948) — order-n approximations with printed samples.
- Lutz, *Stochastische Texte* (1959) — algorithm published alongside outputs.
- Balestrini, *Tape Mark I* (1961) — four rules published in *Almanacco Letterario Bompiani*
  1962; an independent Python reconstruction exists (`fanfani/TAPE-MARK-1`), enabling
  **cross-implementation differential testing** rather than just self-consistency.
- Knowles & Tenney, *A House of Dust* (1967) — FORTRAN source and printed outputs.
- Enzensberger (2000) — four published stanzas; sufficient to recover and verify the 6×6 slot
  schema even though the lexicon is unavailable.

Where the outputs are still in copyright, test against *structural* invariants (slot counts,
POS skeletons, space cardinality) rather than shipping the text.

### 3.3 Examples as fixtures

The collection's entry format is name + definition + example. Every entry with a real example is
already a test case: **the example must validate under its own procedure.** Running this over
the whole collection self-cleans it — a failure is either a wrong validator or a misattributed
example, and both are worth knowing. This scales with the collection rather than competing with
it, and is probably the highest-value CI job in the project.

### 3.4 Property tests

- Generator output always satisfies its own validator (Hypothesis).
- Reversible procedures round-trip: S+7/S−7, letter-shift, homovocalism, cipher constraints.
- Combinatorial generators expose a bijection `index ↔ output`; assert `decode(encode(t)) == t`
  and that sampling without replacement over the index exhausts exactly the declared space size.
  This also gives outputs permanent, citable addresses (the *Sea and Spar Between* property),
  which matters for a package meant to support scholarship.
- Declared space size matches enumerated size for small parameterisations.
- Idempotence / involution where claimed.

### 3.5 Metrics, not predicates

For `[M]` procedures, ship a *score* with a documented range instead of a boolean: phoneme edit
distance for homophonic translation, n-gram overlap for honkadori, semantic drift per hop for
translation relay, distinct-n and self-BLEU for generator diversity. Test the metric's
properties (bounds, monotonicity on constructed cases), not the text's quality.

### 3.6 Meter validators should return confidence

G2P for German via espeak-ng/`phonemizer` is serviceable but wrong often enough that a boolean
"is iambic" will produce false failures. Return a confidence plus the syllabification used, so
failures are debuggable.

---

## 4. Resource layer

Ideas only; the repo may already have settled these.

- **Lexical**: spaCy (en/de/fr) for POS and lemma, `wordfreq` for frequency bands, hunspell or
  Wiktextract for morphology, OdeNet (de) / WordNet (en) for antonymy and synonymy.
- **Phonetic**: `pronouncing`/CMUdict (en), espeak-ng via `phonemizer` (de/fr and fallback),
  Unihan for Chinese tone classes.
- **Script/glyph**: an ascender/descender table for the prisoner's constraint; numeral-value
  tables for Roman, abjad, and gematria chronograms (one shared primitive, three tables).
- **Corpora**: public-domain only for shipped fixtures (Gutenberg, Wikisource, DTA for German).
  Reproducibility demands that dictionary-dependent procedures (S+7 above all) pin a *versioned*
  resource identifier into their output metadata — an S+7 without a named dictionary edition is
  not reproducible, and this is a real scholarly point, not a nicety.

## 5. Licensing note

Much of the canonical Oulipo material is in copyright (Perec, Queneau, Roussel translations,
Enzensberger). Ship **mechanisms plus original or public-domain fillers**, cite the sources, and
keep in-copyright text out of the repo and out of test fixtures. The historical fixtures in §3.2
should be selected with this in mind.

---

## 6. Open questions for the maintainer

1. Does the existing architecture express procedures as compositions, or as individual
   implementations? This determines whether §1 is useful or noise.
2. Is there a single `Procedure` protocol, and does it already carry a validator alongside the
   generator?
3. Can the current model express *sequence* constraints across multiple texts (renga linking,
   cento sourcing, collaborative chains), or is a text the unit of everything?
4. Is granularity a parameter or is it baked into each procedure?
5. Where should the boundary sit between deterministic procedures and model-backed `[M]`
   procedures — same registry with a capability flag, or separate namespaces?
6. Are grammars (Denckring, House of Dust, Tracery) data or code? Data makes the historical
   machines shippable as fixtures and makes remixing a feature.
7. Which of the non-European traditions in §2.7 are worth a dedicated resource investment
   (tone tables, laghu/guru scansion, cynghanedd rules) versus documented-but-unimplemented
   entries in the catalogue?

## 7. Suggested order of attack, if any of this is adopted

1. Erasure/subsequence primitive — one line of validation, unlocks a whole family.
2. Example-as-fixture CI job over the existing catalogue — finds bugs in what already exists.
3. Prefix-decidability flag on existing constraints — cheap, and it is the hook for constrained
   decoding later.
4. Two or three historical grammars as shipped data (House of Dust, loveletters, Denckring) —
   small, demo-able, and they exercise the index-bijection property.
5. Quenine/Queneau-number module — self-contained, mathematically satisfying, good documentation
   centrepiece.
6. One non-European tradition end to end (chandas or lüshi tone patterns are the most tractable)
   as a proof that the abstractions generalize beyond Latin-script letter games.
