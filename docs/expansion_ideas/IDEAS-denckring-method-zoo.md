# denckring — Idea Package: Expanding the Method Zoo

**Status: proposals, not instructions.** This document was written without reading the
current codebase. The implementation is further along than its author knows. Nothing here
overrides existing ADRs, protocols, or naming. Where a proposal conflicts with what is
already built, the existing code wins and this document is wrong.

**Provenance of the ideas below.** Two sources, both new since the last handover:

1. Andreas B. Kilcher, *mathesis und poiesis. Die Enzyklopädik der Literatur 1600 bis 2000*,
   Wilhelm Fink, München 2003, 536 pp. (Habilitationsschrift, Tübingen). Read in full from a
   BSB scan. Page references below are to the printed book and were taken from the scan's
   OCR text layer, which has systematic errors (`det` for `der`, `untet` for `unter`) — grep
   on distinctive nouns, not function words.
2. A multi-source survey of post-2003 scholarship in the same discourse. Items from that
   survey are marked **[survey]** and are *leads to verify*, not confirmed facts. Several
   carry explicit caveats, reproduced here.

**Scope note.** Kilcher's unit of analysis is the *Schreibart* (Litteratur / Alphabet /
Textur), not the *Verfahren*. Most of the book yields text types, which under the project's
existing separation rule belong to the structures collection, not here. The extract below is
deliberately narrow: only material that converts to a procedure with specifiable I/O.

---

## 1. What this proposes, in one paragraph

Nine candidate entries, ranked by how cleanly they convert to code, plus three possible new
generator kinds that none of them fit, plus a metadata pattern for handling disputed
historical counts. The highest-value single addition is Hemeling (1653), which is a named,
dated, primary-source procedure with an explicit combination table and a compound
constraint, and which appears nowhere in the project's prior research. The most
architecturally interesting is Novalis's synkritische method, which is a generator kind the
project does not currently have.

---

## 2. Tier A — verifiable *and* generative

These have a decidable constraint (you can write a test that passes or fails on an output)
*and* a construction procedure. If the catalogue distinguishes entries that ship with a
generator from entries that are description-only, these are generator candidates.

### A1. Letterwechsel / Buchstabenwechsel — Harsdörffer

- **Sources (author-stated):** *Poetischer Trichter*, Nürnberg 1647–1653, II, p. 17;
  *Deliciae Physico-Mathematicae / Erquickstunden*, Bd. 2, p. 514. Via Kilcher pp. 373–376.
- **Procedure:** letters of a proper name are rearranged until a new sense emerges.
  Harsdörffer gives the physical algorithm: write each letter on a small paper slip or —
  because paper blows away — on a wooden die; **separate the vowels (`Stimmer`) from the
  consonants (`Mitstimmer`)**; shuffle until other words come out. He also notes the Dutch
  term `Letterkeer`.
- **I/O:** input = a proper name (string). Output = a permutation of its letters forming
  lexical units.
- **Verification:** multiset equality of characters against the source string, plus lexicon
  membership of the output tokens.
- **Why it is not a duplicate:** this permutes *letters*. The Proteus verse entry permutes
  *words*. If the catalogue currently has only one anagram-shaped entry, this is a split.
- **A constraint worth preserving:** Harsdörffer's stated appeal is that the result belongs
  to the person whose name it was drawn from. That makes the input a named entity, not
  arbitrary text — worth encoding as a type constraint rather than dropping as flavour.

### A2. Hemeling — *Arithmetische Letter- oder BuchstabWechslung* (1653)

- **Full title (per Kilcher p. 376):** *Arithmetische Letter- oder BuchstabWechslung. Das
  ist: Kurtze Anleitung / welcher massen Anagrammata / Letter- oder Buchstab-wechsele zu
  machen / und durch Reime zu erklähren.*
- **Why this is the best single addition:** it is a **compound constraint**, and both halves
  are checkable. Stage 1: the anagram. Stage 2: the anagram must be **explicated in rhymed
  verse**. Nothing else surveyed gives a rule that tight.
- **Also specified:** a `Buchstabenwechsel-Tafel` that pre-computes combinations up to six
  elements, and lettered dice played across that table as a board. So the historical device
  is a table + dice, i.e. a bounded enumerator plus a random-draw front end.
- **Historical honesty worth recording:** Hemeling explicitly notes the *limits* — as
  elements are added the count grows unmanageably. The source itself frames combinatorial
  explosion as a constraint on the method. That belongs in the entry's `Definition`.
- **Status:** new primary source. Not in the project's earlier Llull/Kircher/Harsdörffer/
  Jean Paul research pass.

### A3. Versus palindromus

- **Source:** one of Leibniz's own headings in *Dissertatio de arte combinatoria* (1666),
  alongside `Poetices Proteus` and `Anagrammata`, at examples ranging from Scaliger to
  Harsdörffer. Kilcher p. 373, citing Leibniz, *Philosophische Schriften* Bd. 4, S. 86ff.
- **Why bother with something this obvious:** it gives *author-stated* provenance under the
  project's existing provenance convention. A palindrome entry sourced to Leibniz's own
  taxonomy is stronger than one sourced to general knowledge.
- **Verification:** trivial. Generation: search under a lexicon.

### A4. Anagrammata as a Leibniz-catalogued category

Same source and same argument as A3. Worth checking whether the catalogue currently treats
anagram as a modern generic entry; if so, it can be re-sourced to the 1666 taxonomy and
placed as the parent of A1 and A2.

---

## 3. Tier B — generative, partially verifiable

### B1. Novalis — synkritische Wissenschaftslehre / cross-domain terminology transfer

- **Source:** Kilcher pp. 402–415, esp. "Die Erneuerung der kombinatorischen Enzyklopädik"
  p. 408ff, on the *Allgemeines Brouillon*.
- **Kilcher's formulation, paraphrased:** the individual sciences and their terminologies are
  mutually convertible into one another and configurable with one another; the systematicity
  lies not in a vertical hierarchy of logical propositions but in the **horizontal,
  syntagmatic combinatorics** of ideas, concepts and images. Novalis calls it a *synkritische
  Wissenschaftslehre* and rehabilitates the category of the "Aggregat" that Fichte used
  polemically.
- **As a procedure:** take the lexicon of discipline A, apply it to domain B. This is what
  produces the characteristic Brouillon entries.
- **I/O:** input = (source-discipline term list, target domain). Output = statements about
  the target domain phrased in the source discipline's vocabulary.
- **Verification:** vocabulary-level — output must draw from A's term list while remaining
  topically in B. Weaker than Tier A, but decidable enough for a test.
- **Why it matters architecturally:** this is the one candidate that plays to a language-model
  backend rather than a permutation engine. See §5.

### B2. Reimlexikon as a production instrument

- **Source:** Kilcher pp. 231–244 ("Enzyklopädische Ordnung des Reimlexikons").
- **Kilcher's claim:** rhyme dictionaries are *operative instruments* of a formalised poetics,
  not reference works; in most European literatures they predate the general language
  dictionary; their nomenclature is noun-heavy and deliberately includes proper names,
  historical and geographical names, and the terminologies of the arts and sciences.
  Example given: Pierre Richelet, *Dictionnaire de rimes* (1692, expanded 1751).
- **As a procedure:** compose under a closed rhyme-class inventory.
- **Blocker:** this needs rhyme data. The project's earlier landscape survey already
  identified German rhyme dictionaries as a greenfield gap. So B2 is blocked on a *data*
  problem, not a design problem — file the entry, defer the generator.

### B3. Diderot — the theory of *renvois*

- **Source:** Kilcher pp. 252–265, in two parts ("Enzyklopädische Theorie der Verweise" /
  "Ästhetische Theorie der Verweise").
- **The point:** Diderot takes the labyrinth as the *paradigm* of encyclopedic organisation
  rather than as its counter-model, against d'Alembert's Cartesian-mathematical tree. The
  cross-reference network carries the argument.
- **As a procedure:** generate an article network in which the renvois do the work.
- **Verification:** structural only — no orphan nodes, every article links out, links must
  cross domain boundaries. That is a weak test.
- **Recommendation:** file as a catalogue entry without a generator until there is a decision
  on whether graph-level checks count as verification. See §5.

---

## 4. Tier C — the Jean Paul pipeline (a split, not an addition)

Kilcher's "Typologie enzyklopädischer Aufschreibetechniken", p. 383ff, is the most directly
useful passage in the book for this project. It splits Jean Paul's papers into **three text
types that are also three poetological steps**:

1. **Exzerpte** — verbatim copies with precise source attribution, concentrated 1778–1790.
   Initially "Verschiedenes aus den neuesten Schriften"; from the Leipzig years onward
   organised into long-running subject series (`Geschichte` from 1782, `Natur` from 1790,
   `Geographie` from 1791).
2. **Miszellaneen** — the shift away from thematically ordered *Kollektaneen*. Kilcher:
   mixture becomes the principle; what has been read is reassembled **without regard to
   context or evaluation**. He describes the reading itself changing — cursory-thematic to
   statarisch-dynamic, digressive, closer to leafing than to reading.
3. **Register** — "Exzerpte aus Exzerpten". A 1244-page alphabetically ordered register whose
   162 entries thematically restructure the excerpt mass and condense it to short sentences.
   Probably the *Lexicon Jean-Paullinum* Jean Paul mentions in 1803. Used as an orientation
   aid *and* as the instrument of his poetic `inventio`.

**Proposal:** if the current design has a single `Ideenwuerfeln` entry, it is collapsing three
separable procedures with distinct I/O. Consider splitting, with `Ideenwuerfeln` as the
collision step that sits on top of the register layer rather than as the whole pipeline.

**Prior art worth recording:** Kilcher shows the discipline-keyed excerpt scheme derives from
Daniel Georg Morhof's *Polyhistor* (`Excerpta Physica`, `Mathematica excerpta`, `Loci
communes Historici`, `Loci communes Morum`, `Collectanea Medica`, `Collectanea Chymica`,
etc.). That is a named historical precedent for corpus partitioning — useful for the corpus
layer's documentation.

### C1. A design constraint, not an entry — Kilcher p. 390

Kilcher's section "Kombinatorik, Assoziation, Witz als enzyklopädische Verfahren" argues that
Jean Paul **de-mathematises** the Lullian ars: he takes it not as a mathematical-cybernetic
regulation of knowledge but inverts it into a procedure of *deregulation*, associatively
linking dissociated particles. The defining feature is the **arbitrary course** — the
relation of elements happens unconsciously and by chance, not by rule. Jean Paul explicitly
separates the combinatorial operation of the imagination (which waits on "Kombinazionen des
Zufalls") from the more rational `Scharfsinn`. He also claims the harder the combination, the
greater the yield.

**Implication for the sampler:** this is an argument *against* similarity-weighted or
semantic-neighbour retrieval and *for* uniform random draw across the whole corpus. The
distance between the collided elements is the productive feature, not noise to be minimised.
Worth an explicit comment in the sampler, because the "obvious improvement" of adding
embedding-based retrieval would be historically wrong here.

---

## 5. Possible new generator kinds

The existing kinds are `product`, `permutation`, and `sample` (with `sample` introduced for
the corpus layer). Three candidates above do not fit any of them:

| Candidate | Shape | Suggested kind |
|---|---|---|
| Leibniz's 1679 numerical characteristic | concept pair in → boolean out | `validator` |
| Novalis synkritisch (B1) | lexicon A + domain B → text in A's vocabulary | `transfer` |
| Diderot renvois (B3) | node set → linked graph | `network` |

`validator` is the cheapest and most general: a constraint with no construction procedure.
Many entries in the catalogue probably already have a checkable constraint but no generator;
formalising that as a kind would let those entries carry tests. It also gives a home for
Leibniz's prime-factor encoding of concepts (from the April 1679 manuscripts, where
predication reduces to divisibility — *animal* 2, *rational* 3, *man* 6), which is otherwise
homeless: it has crisp I/O but generates nothing.

`transfer` is the one that changes what the library can do, because it presumes a language
model rather than a combinatorial engine. That may be out of scope by design — if so, B1
becomes a description-only entry and this table shrinks.

---

## 6. Metadata pattern — disputed historical counts

The project already bars hard-coding the disputed Denckring figure. The survey turned up
enough conflicting numbers to suggest generalising that from a one-off rule into a field.

Reported ring inventory (48 prefixes / 50 initial letters or diphthongs / 12 medial letters /
120 final letters or diphthongs / 24 suffixes):

- Raw product: 48 × 50 × 12 × 120 × 24 = **82,944,000**
- Trettien (Electronic Literature Directory): **97,209,600**
- Hundt, *"Spracharbeit" im 17. Jahrhundert* (De Gruyter 2000), fn. 135, p. 285:
  **101,606,400**

**Neither published figure equals the raw product**, and neither source states its counting
assumptions (blank slots? a different disc inventory? the 48/50 label discrepancy already
noted in the project's earlier research?). **[survey]** also reports that Harsdörffer relied
on figures from Lauremberg, Puteanus and Etten that were wrong, and that Leibniz produced the
first correct computation — traced to Knobloch (1973) pp. 41–43 and Zeller (1974) p. 172,
neither of which has been read directly.

**Proposal:**

```
positions: [48, 50, 12, 120, 24]
computed_total: 82944000          # derived, never stored by hand
disputed_totals:
  - value: 97209600
    source: "Trettien, Electronic Literature Directory"
  - value: 101606400
    source: "Hundt 2000, fn. 135, p. 285"
notes: "Published totals do not reconcile with the product of the stated
        inventory; counting assumptions unstated in both sources."
```

**Revision threshold:** if Knobloch (1973) or Zeller (1974) is obtained with an explicit
derivation, promote that to canonical and demote the rest.

The same pattern applies wherever a secondary source asserts a count the primary inventory
does not support. Making it a field rather than a special case means the next such conflict
is cheap.

---

## 7. Optional — Kilcher's paradigm axis as a tag

Kilcher's three paradigms (`Litteratur` / `Alphabet` / `Textur`) classify what a procedure is
*for* rather than how it computes, which is orthogonal to the generator-kind axis.

**Argument for:** it gives a second, scholarly-defensible facet for browsing a 500-entry
catalogue, sourced to a citable Habilitationsschrift.

**Argument against, and it is real:** the categories are *epochal*. A procedure's paradigm
depends on when it was practised, so a modern Oulipian revival of a Baroque device lands in a
different bucket than the original. That either needs a per-instance rather than per-entry
tag, or the axis needs to be dropped.

**Recommendation:** ADR before adoption, not adoption then ADR.

---

## 8. Explicitly *not* proposed

The following appear prominently in Kilcher and should stay out of the method zoo. They are
`Schreibweisen` with no specifiable rule, and forcing a generator onto them would be a
category error:

- **Witz** and **Assoziation** (pp. 390–401) — the productive step is human recognition of
  hidden similarity. This is the same conclusion the project's own Ideenwürfeln
  reconstruction reached; do not relitigate it.
- **Arabeske** as an encyclopedic Schreibweise (Schlegel, pp. 427–431).
- **Montage / Allegoristik** (Benjamin, Arno Schmidt's Zettel, pp. 436–461) — belongs to the
  structures collection if anywhere.
- **Der Exkurs** (the "Exkurs über den Exkurs", p. 136) — digression is describable as a rule
  ("interrupt at defined points, insert material from another domain") but Kilcher does not
  specify the points, and inventing them would be reconstruction presented as author-stated.

Everything in this section is still legitimate *catalogue* material under a
description-only entry type. The exclusion is from the generator layer, not from the book.

---

## 9. Leads to verify — **[survey]**, none confirmed

These came from a multi-source survey rather than from a read source. Each needs checking
before it enters the catalogue.

**Existing implementations worth studying as models:**

- Andrew Cashner, "Athanasius Kircher's *Arca musarithmica* (1650) as a Computational
  System", reported in *Journal of Creative Music Systems* 8.1 (2024), with a **Haskell
  implementation** at `github.com/andrewacashner/kircher` and `arca1650.info`. If this is as
  described, it is the closest existing analogue to what denckring is doing — a peer-reviewed
  paper plus running code for a Baroque combinatorial device. Worth reading before finalising
  the entry schema.
- *Ramon Llull: From the Ars Magna to Artificial Intelligence*, eds. Alexander Fidora &
  Carles Sierra (IIIA-CSIC, Barcelona, 2011; reportedly open access) — reported to formalise
  "the four algorithms of Llull's Ars" precisely enough to implement.
- **Reported gap:** no maintained public interactive Denckring simulator or repository. A
  transcription plus animated reconstruction is reported at `digitalcraft.org`; Trettien's
  2009 MIT thesis functions as a combinatory web-text. If the gap is real, a clean cited
  implementation would be a citable contribution rather than just a utility.

**New primary sources for the Jean Paul layer:**

- *Jean Paul: Exzerpte. Digitale Edition* (Arbeitsstelle Jean-Paul-Edition, Würzburg) —
  already known to the project. **[survey]** reports over 12,000 manuscript pages and more
  than 100,000 entries. Rights caveat from the earlier research still stands: the
  transcription carries its own rights distinct from the public-domain manuscript; contact
  the Arbeitsstelle before any distribution.
- Historisch-kritische Ausgabe, II. Abteilung (Nachlass), **Bd. 9: *Einfälle, Bausteine,
  Erfindungen*** (De Gruyter; text 2020, commentary 9.3). Kilcher, writing in 2003, could
  only note this volume as announced. **[survey]** reports it appeared and that the
  "Erfindungen" contain Jean Paul's own rules for the *Fabelarchitektur* of the novels — i.e.
  potentially author-stated procedures rather than reconstructions. Highest-value lead in
  this section.
- Michael Will, *Findbuch zu Jean Pauls Exzerpten* (Königshausen & Neumann, 2021) — reported
  to be the first study of the "Exzerptenexzerpte" and the register's own register.
- Andrea Krauß, "Sammeln – Exzerpte – Konstellation. Jean Pauls literarische Kombinatorik",
  *Monatshefte* 105.2 (2013), 291–314.

---

## 10. Suggested order of work

1. **A2 (Hemeling)** — highest value per unit effort, and the compound constraint will
   exercise whatever multi-stage validation the harness has.
2. **A1 / A3 / A4** — cheap, and they tidy the anagram family under Leibniz's own taxonomy.
3. **The Tier C split**, if `Ideenwuerfeln` is currently monolithic. Do this before the
   corpus layer hardens, not after.
4. **The `validator` kind** (§5), if the architecture tolerates a kind that generates nothing.
   It unlocks Leibniz 1679 and probably several existing entries.
5. **§6 metadata pattern** — small, and it prevents the next count dispute from being a
   special case.
6. **B1 (Novalis)** only if a language-model backend is in scope. Otherwise
   description-only.

B2 stays blocked on rhyme data. B3 stays description-only pending a decision on graph-level
verification.

---

## Appendix — page map for *mathesis und poiesis*

| Section | Pages | Relevance |
|---|---|---|
| Exkurs über den Exkurs | 136 | digression; not implementable |
| Enzyklopädische Ordnung des Reimlexikons | 231–244 | B2 |
| Diderot I / II: Theorie der Verweise | 252–265 | B3 |
| Stochastische Lektüre im Lexikonroman | 271–275 | reading-side procedure, unexamined |
| Satirische Wörterbücher | 289–309 | unexamined |
| Lullische Kybernetik | 357–369 | already covered by facsimile research |
| Kombinatorische Poetik / Sprachalchemie | 370–378 | **A1, A2, A3, A4** |
| Exzerptenenzyklopädik (Jean Paul) | 380–401 | **Tier C**, incl. typology at 383ff |
| Kombinatorik, Assoziation, Witz | 390–395 | **C1 design constraint**; §8 exclusions |
| Novalis, "Confusions-System" | 402–415 | **B1** |
| Schlegel, Fragment und Totalität | 416–431 | §8 exclusion |
| Montage (Benjamin, Arno Schmidt) | 436–461 | §8 exclusion |
| Maschine / literarische Universalmaschinen | 462–481 | unexamined; scan is defective near 481 |

Three sections were not examined closely and may repay a second pass: stochastic reading in
the Lexikonroman (271), the satirical dictionaries (289–309), and the universal-machine
chapter (462–481). The scan has a structural defect around page 481, so that one needs
visual inspection rather than text extraction.
