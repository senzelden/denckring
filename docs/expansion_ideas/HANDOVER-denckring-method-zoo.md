# denckring — Method Zoo: Ideas, Schema Proposals, and Sources

Proposals, not instructions. Written without access to the codebase, so where anything here
conflicts with what exists, what exists wins. Consolidates three earlier working documents.

Two sources underlie the material: Andreas B. Kilcher, *mathesis und poiesis. Die Enzyklopädik
der Literatur 1600 bis 2000* (Fink, 2003), read in full from a scan; and a survey of post-2003
and cross-cultural scholarship. Page references are to Kilcher's printed book. Items marked
**[survey]** are leads that have not been verified against a primary source.

Two accompanying HTML files (`denckring-workbench.html`, `denckring-workbench-ii.html`) are
executable sketches written to make the arguments visible, especially the ones about what
fails. They are not specifications, and their corpora must not be lifted into the package —
see §10.

---

## 1. The devices, sorted by what they can actually do

### 1.1 Ship as generators

**Indexed rings** — Llull, *Ars brevis* (1308). The design commitment worth keeping is that the
letters are an *index*, not a vocabulary: B is simultaneously *bonitas*, *differentia*, *utrum*
and *Deus* depending on which column you read. One symbol, parallel projection tables. Most
modern combination wheels put different word lists on each ring, which produces a mad-lib rather
than an ars. Keep the index/projection split and content swaps become free.

**Mixed-radix odometer** — the Denckring shape. Rings of unequal length, so a configuration is
an integer in a non-uniform base. See §7 on the counts.

**Corpus-derived rings** — no historical precedent, and the only genuinely contemporary
capability in the whole set. Ring contents extracted from a text at load time (frequency against
a stoplist, or clustering). Structure fixed and enumerable, content input-dependent. Cheap.

**Prastāra / naṣṭa / uddiṣṭa** — Piṅgala, *Chandaḥśāstra*, c. 3rd–2nd c. BCE. Enumeration of all
light/heavy syllable patterns of length n, with two *named* inverse functions. See §2.3.

**Root permutation with validity mask** — al-Khalīl ibn Aḥmad al-Farāhīdī, *Kitāb al-ʿAyn*,
8th c. Enumerate all n! orderings of a root's consonants, then flag which are realised and which
are *muhmal*, neglected. See §2.2 — the mask is the valuable part.

**Letterwechsel / Buchstabenwechsel** — Harsdörffer, *Poetischer Trichter* II p. 17;
*Deliciae/Erquickstunden* Bd. 2 p. 514; via Kilcher pp. 373–376. Letters of a proper name
rearranged until new sense emerges. Harsdörffer gives the physical algorithm: write each letter
on a slip or — because paper blows away — on a wooden die; **separate the vowels (`Stimmer`)
from the consonants (`Mitstimmer`)**; shuffle until words come out. He notes the Dutch term
*Letterkeer*. Not a duplicate of Proteus verse: this permutes letters, that permutes words.
Worth preserving as a type constraint: Harsdörffer's stated appeal is that the result belongs to
the person whose name it was drawn from, so the input is a named entity, not arbitrary text.

**Versus palindromus** and **Anagrammata** — two of Leibniz's own headings in *Dissertatio de
arte combinatoria* (1666), alongside `Poetices Proteus`, with examples from Scaliger to
Harsdörffer (Kilcher p. 373, citing *Philosophische Schriften* Bd. 4 S. 86ff). Trivial to
implement; the value is author-stated provenance for constraints that would otherwise be sourced
to general knowledge. Anagrammata is the natural parent of Letterwechsel and Hemeling.

### 1.2 Ship, but not as generators

**Hemeling** — see §2.1. A validator with a compound constraint.

**Temurah** — atbash, albam, cyclic shift. A bijection over 22 letters that transforms an input
rather than enumerating a space, so it has no address and no total. Trivially implementable,
which is exactly why it will look more important than it is.

**Excerpt collision** — Jean Paul. A sampler whose defining constraint is historical rather than
technical. See §8.

**Reimlexikon** — Kilcher pp. 231–244. Rhyme dictionaries as *operative instruments* of a
formalised poetics rather than reference works; in most European literatures they predate the
general language dictionary, and their nomenclature is noun-heavy, deliberately including proper
names and the terminologies of the arts and sciences (example: Richelet, *Dictionnaire de
rimes*, 1692). The constraint is testable but blocked on rhyme data, which the earlier landscape
survey already identified as a greenfield gap. File the entry, defer the generator.

**Novalis — synkritische Wissenschaftslehre** — Kilcher pp. 402–415, esp. p. 408ff on the
*Allgemeines Brouillon*. The sciences and their terminologies are mutually convertible and
configurable; systematicity lies in horizontal, syntagmatic combinatorics rather than a vertical
hierarchy of propositions. As a procedure: take the lexicon of discipline A, apply it to domain
B. Verifiable at the vocabulary level. Only survives as a generator if a language-model backend
is in scope; otherwise description-only.

### 1.3 Do not ship

**Zāʾirja** — Ibn Khaldūn, *Muqaddimah*. Structurally the closest thing in any tradition to
Llull's revolving figures: concentric lettered rings plus a table, worked with a numerical
procedure. The structure is attested; the operating procedure as transmitted is not reliably
reconstructable and published reconstructions disagree. Building an interactive version means
inventing the disputed steps and presenting the invention as the device.

**Renvois** — Diderot, Kilcher pp. 252–265, in two parts (encyclopedic then aesthetic theory of
cross-references), with the labyrinth taken as the *paradigm* of encyclopedic organisation rather
than its counter-model, against d'Alembert's Cartesian tree. Generative as a structure;
verifiable only structurally — no orphans, every article links out, links cross domains. That is
a weak test, and the workbench demonstrates why by generating a network that passes every check
and is obviously nonsense.

**Shikimoku** — renga linking rules. Not "never", but "not until backtracking exists". A
forward-only sampler provably paints itself into corners: at chain length 36 with separation
intervals enforced, the workbench version runs out of legal moves and has to place an illegal
verse. The historical codes assume revision; filter-as-you-go cannot model them.

**The 231 gates** — *Sefer Yetzirah*. C(22,2) with a no-repeat rule is the existing product kind
with n=22, k=2. No new mechanism. What is worth filing is the factorial ladder the text states
directly (2 stones → 2 houses, 3 → 6, 4 → 24, 5 → 120) as an author-stated citation for
permutation counting, roughly a millennium before Leibniz's taxonomy. A provenance note on an
existing entry, not an entry.

---

## 2. The three highest-value items

### 2.1 Hemeling — the tightest rule in the European material

Johann Hemeling, *Arithmetische Letter- oder BuchstabWechslung. Das ist: Kurtze Anleitung /
welcher massen Anagrammata / Letter- oder Buchstab-wechsele zu machen / und durch Reime zu
erklähren* (1653). Via Kilcher p. 376.

It is a **compound constraint** and both halves are checkable. Stage one: the anagram, verified
by multiset equality of letters against the source plus lexicon membership. Stage two: the
anagram must be **explicated in rhymed verse**, verified by a rhyme-scheme test on the gloss.
Nothing else in the surveyed material gives a rule this tight.

Also specified: a *Buchstabenwechsel-Tafel* pre-computing combinations up to six elements, and
lettered dice played across it as a board — a bounded enumerator with a random-draw front end.
And a piece of historical honesty worth recording in the entry: Hemeling explicitly notes that as
elements are added the count grows unmanageably. The source itself frames combinatorial
explosion as a constraint on the method.

New primary source; absent from the project's earlier Llull/Kircher/Harsdörffer/Jean Paul pass.

### 2.2 The muhmal mask is a field, not a kind

Al-Khalīl enumerates the whole permutation space and then marks which members are attested and
which are neglected. Structurally: a ring device plus a validity mask.

Best single addition available. It retrofits onto every ring device already built, it is a schema
change rather than a new protocol, and it produces a generator that knows which of its own
outputs are real — validation and generation in one pass. It also gives a principled home for
the thing every combinatorial device produces in bulk, which is garbage.

```
mask:
  kind: lexicon | predicate | enumerated
  source: <lexicon id, or the entry supplying the predicate>
  coverage: 3/6            # computed, never stored by hand
  unmarked_policy: hold    # hold | drop
```

`hold` is the historically faithful default. Al-Khalīl does not discard the muhmal forms; he
enumerates and flags them. That distinction is the intellectual content of the device.

### 2.3 Prastāra is the citation for the address protocol

Piṅgala names both directions of the index function: `naṣṭa` is address→pattern, `uddiṣṭa` is
pattern→address. The classical rule works by repeated halving and is equivalent to the binary
reading in the two-symbol case.

This converts "a device is an odometer" from a modern reading into an attested procedure from
roughly the 2nd–3rd century BCE. The binary reading is defended in peer-reviewed work — B. van
Nooten, "Binary Numbers in Indian Antiquity," *Journal of Indian Philosophy* 21.1 (1993): 31–50,
arguing binary calculation existed in India as the science of metrics well before Leibniz. Jayant
Shah, "A History of Piṅgala's Combinatorics" (2008), formalises the algorithms. Related: the
*meru-prastāra* (Pascal's triangle) for counting patterns by syllable weight, and the
Gopāla–Hemachandra sequence.

Convention caveat: sources differ on which end of a *prastāra* row is the low-order position and
on which syllable maps to which digit. State the choice in the entry; do not present it as *the*
convention.

---

## 3. The layer split

**The problem.** Nobody writes poems with the 231 gates or with Ifá. Those are not writing
procedures; they are knowledge-ordering instruments. Admitting them changes the collection's
implicit thesis from "500 ways to generate text" to "a taxonomy of combinatorial cognition", and
changes the acceptance test from *does this produce usable output* to *is the mechanism
faithfully specified*. Under the second test a device that produces nothing interesting is still
a first-class entry — which is what temurah, the divination systems and the zāʾirja need.

**The proposal.** Don't choose between the two projects and don't fork the collection. Split the
axis inside it:

- **`Verfahren`** — acceptance test: run it, get text. Keeps the 500 target and keeps it honest.
- **`Instrument`** — acceptance test: the mechanism is faithfully formalised and sourced. Output
  optional.

Same schema, same provenance rules, same file layout. Different acceptance criteria and
**separate counters**. The 500 target belongs to `Verfahren` only.

**Costs, stated plainly.** Scope becomes unbounded once classification schemes are admissible.
The scholarly bar rises, and it has already bitten several times in the course of this work. Two
counters is a maintenance cost that pays off only if the second is genuinely used.

**Kill criterion.** If after twenty `Instrument` entries none has changed how a `Verfahren` entry
is modelled, the layer is decoration and should be dropped. Two test cases are already in play:
the muhmal mask (§2.2) and the index↔pattern protocol (§2.3), both of which came from the
instrument side and improve the generator side.

---

## 4. Four primitives, and the schema they imply

The reason the instrument layer is coherent rather than a dumping ground: four primitives recur
across every tradition surveyed. Building the layer around them turns the cross-cultural
comparison from rhetoric into something operational — and that operationalisation appears to be
the thing nobody has done.

**Address space.** A finite configuration set with a stable integer index. Ifá's 256 (16 odu × 2
positions), the Yijing's 64, the Taixuanjing's 81, the Denckring's five unequal rings, Llull's 9³.

```
address_space:
  radix: [16, 16]          # or [2,2,2,2,2,2], [3,3,3,3], [48,50,12,120,24]
  size: 256                # computed from radix, never stored by hand
  ordering: natural        # natural | traditional | disputed
  ordering_note: "King Wen sequence differs from natural binary order"
```

`ordering` matters more than it looks. Natural binary order is what the Yijing's address
arithmetic produces; King Wen is a lookup table, easy to get wrong from memory. Ifá odu names and
sequence vary between traditions. Make ordering an explicit sourced field, not an implicit
choice.

**Enumeration.** The systematic laying-out of every configuration. *Prastāra* is the named
instance; every ring device does it implicitly.

**Index↔pattern bijection.** The inverse pair. See §2.3.

**Sequence constraint.** Rules over what may follow what, with separation intervals — as against
every other primitive, which governs co-occurrence within one draw. *Shikimoku* is the developed
instance. No rigorous scholarly comparison of shikimoku to Oulipo constraints appears to exist,
so this is both a schema gap and a small publishable finding.

---

## 5. Kinds

| Kind | Primitive exercised | Members |
|---|---|---|
| `product` / `permutation` | address space + enumeration | ring devices, root permutation, 231 gates |
| `sample` | address space, drawn not walked | excerpt collision, divination casts |
| `validator` | none — membership test only | Letterwechsel, Hemeling, Leibniz 1679 |
| `transform` | none — bijection over inputs | temurah |
| `sequence` | sequence constraint | shikimoku; needs backtracking |
| `transfer` | none — semantic move | Novalis synkritisch; needs an LM backend |
| *(mask, a field)* | attaches to enumeration | al-Khalīl; retrofits everywhere |

`validator` is the cheapest and most general, and it gives a home to Leibniz's 1679 numerical
characteristic — concept pair in, boolean out, predication reduced to divisibility (*animal* 2,
*rational* 3, *man* 6) — which has crisp I/O but generates nothing. `transform` and `sequence`
are genuinely new shapes and both come from the instrument side, which is §3's argument in
miniature.

---

## 6. Contested edges as a schema feature

The catalogue will accumulate influence claims. Several are unsettled, and the unsettled ones are
exactly the ones that make the collection look most coherent — so they need a structure rather
than a judgement call.

```
influence:
  from: zairja
  to: llull-ars
  status: contested
  proponents:
    - "David Link, 'Scrambling T-R-U-T-H', in Variantology 4 (König, 2010)"
    - "Daniel Libeskind (popular)"
  skeptics:
    - "Anthony Bonner, The Art and Logic of Ramon Llull (Brill, 2007) — grounds the Ars
       in the Divine Dignities and Augustinian/Neoplatonic theology"
    - "Umberto Eco — distinguishes inventive from divinatory combinatorics"
  objection: "Chronology. Ibn Khaldun (1332-1406) wrote the Muqaddimah in 1377; Link's own
              evidence has al-Marjani introducing him to the procedure at Biskra in 1370/71.
              Llull died 1316. Transmission requires undocumented earlier circulation."
  source_quality: "pro-transmission material skews to non-peer-reviewed venues; Link is the
                   serious exception but writes within a media-archaeology programme"
```

**zāʾirja → Llull.** Not the scholarly consensus. Even scholars who accept Arabic influence
(Dominique Urvoy, *Penser l'Islam*, 1980; Charles Lohr) argue for diffuse cultural immersion, not
derivation from this device. The safest current model is comparison without transmission — a 2023
framing **[survey]** (Bottomley & Dalla Costa, "Ars combinatoria," Routledge) treats the zāʾirja,
Llull's *Ars* and Alberti's cipher disk as three comparable objects of rotating symbols without
asserting a line between them. Bonner's exact wording could not be verified from open sources;
his skepticism is inferred from his alternative genealogy. **Verify against the Brill 2007 text
before quoting him.**

**Africa → Islamic geomancy → Europe → Leibniz.** Ron Eglash, *African Fractals* (Rutgers, 1999)
proposes it; the historical evidence is comparatively weak, and the "weak evidence"
characterisation is a critic's paraphrase, not Eglash's own. Stephen Skinner, and Savage-Smith &
Smith (*Magic and Divination in Early Islam*, 2004), are the more rigorous treatments of the
geomancy line. File as hypothesis with named parties.

---

## 7. Disputed counts

Generalise beyond the Denckring: wherever a secondary source asserts a count the primary
inventory does not support, make it a field rather than a special case.

| Figure | Attribution | Status |
|---|---|---|
| 82,944,000 | 48 × 50 × 12 × 120 × 24, computed | arithmetic on the standard inventory |
| 97,209,600 | Trettien, Electronic Literature Directory; a later survey attributes the same figure to *Leibniz's own 1666 calculation* **[survey]** | attribution unverified; still doesn't match the product |
| 101,606,400 | Hundt, *"Spracharbeit" im 17. Jahrhundert* (2000), fn. 135 p. 285 | counting assumptions unstated |

```
positions: [48, 50, 12, 120, 24]
computed_total: 82944000
disputed_totals:
  - {value: 97209600, source: "Trettien, ELD; Leibniz attribution unverified"}
  - {value: 101606400, source: "Hundt 2000, fn. 135, p. 285"}
notes: "Published totals do not reconcile with the product of the stated inventory;
        counting assumptions unstated in both sources."
```

The Leibniz attribution is the tempting one, because a figure computed by Leibniz sounds
authoritative. Resist it: it arrived through a secondary survey without a primary citation, and
adopting it would mean asserting Leibniz computed a number that is not the product of the rings
as the same sources describe them. Record it as a third disputed attribution and keep computing.

**Revision threshold:** an explicit derivation in Knobloch (1973) 41–43 or Zeller (1974) 172,
read directly. **[survey]** also reports that Harsdörffer relied on figures from Lauremberg,
Puteanus and Etten that were wrong; neither source has been read.

Source for the plate: *Deliciae Mathematicae et Physicae*, Nürnberg 1651, **Zweyter Theil,
p. 517** (modern ed. Jörg Jochen Berns, Keip, 1990) — not the *Dritter Theil* (1653), which
contains related discussion. Confirm against a physical copy before citing.

---

## 8. Design constraints that are not entries

**The sampler must not use similarity retrieval.** Kilcher p. 390, "Kombinatorik, Assoziation,
Witz als enzyklopädische Verfahren": Jean Paul *de-mathematises* the Lullian ars, taking it not as
a mathematical-cybernetic regulation of knowledge but inverting it into a procedure of
*deregulation*, associatively linking dissociated particles. The defining feature is the
arbitrary course — relations arise unconsciously and by chance, not by rule. He separates the
combinatorial operation of the imagination, which waits on "Kombinazionen des Zufalls", from the
more rational *Scharfsinn*, and claims the harder the combination, the greater the yield.

So: uniform random draw across the whole corpus, not embedding-based neighbours. The distance
between the collided elements is the productive feature, not noise. Put this in a comment in the
sampler, because the "obvious improvement" of adding semantic retrieval would be historically
wrong, and the workbench demonstrates the collapse it causes.

**If history-dependence is wanted, make it anti-preferential.** Down-weighting what the user
already kept pushes the next draw into unvisited parts of the space; preference-weighting
collapses the device into a local basin within a few dozen draws.

---

## 9. The Jean Paul pipeline is a split, not an addition

Kilcher's "Typologie enzyklopädischer Aufschreibetechniken" (p. 383ff) divides Jean Paul's papers
into three text types that are also three poetological steps:

1. **Exzerpte** — verbatim copies with precise source attribution, concentrated 1778–1790.
   Initially "Verschiedenes aus den neuesten Schriften"; from the Leipzig years organised into
   long-running subject series (`Geschichte` 1782, `Natur` 1790, `Geographie` 1791).
2. **Miszellaneen** — the shift away from thematically ordered *Kollektaneen*. Mixture becomes the
   principle; what has been read is reassembled **without regard to context or evaluation**.
   Kilcher describes the reading itself changing — cursory-thematic to statarisch-dynamic,
   digressive, closer to leafing than to reading.
3. **Register** — "Exzerpte aus Exzerpten". A 1244-page alphabetical register whose 162 entries
   restructure the excerpt mass into short sentences. Probably the *Lexicon Jean-Paullinum* he
   mentions in 1803. Used as an orientation aid *and* as the instrument of poetic *inventio*.

If `Ideenwuerfeln` is still monolithic, it collapses three separable procedures with distinct
I/O. Split them, with `Ideenwuerfeln` as the collision step sitting on top of the register layer
rather than as the whole pipeline. Do it before the corpus layer hardens.

Prior art worth recording: the discipline-keyed excerpt scheme derives from Morhof's *Polyhistor*
(`Excerpta Physica`, `Mathematica excerpta`, `Loci communes Historici`, `Loci communes Morum`,
`Collectanea Medica`, `Collectanea Chymica`) — a named historical precedent for corpus
partitioning.

---

## 10. Prior art, interop, and what not to reimplement

**Study as the quality model.** Andrew Cashner's *Arca musarithmica* work: a faithful literate
reconstruction in Haskell (github.com/andrewacashner/kircher, arca1650.info) published as a
specification-plus-implementation paper in the *Journal of Creative Music Systems* 8.1 (2024),
with a companion in *Anuario Musical* 77 (2022) identifying a fourth surviving physical Arca in a
c. 1690 Puebla manuscript. One device, one culture, done properly. Read the JCMS paper before
finalising the entry schema. **[survey]**

**Formal statement of Llull's algorithms.** *Ramon Llull: From the Ars Magna to Artificial
Intelligence*, eds. Alexander Fidora & Carles Sierra (IIIA-CSIC, 2011; reportedly open access),
which formalises "the four algorithms of Llull's Ars". **[survey]**

**Depend on rather than reimplement.** The Sanskrit computational ecosystem already does scansion
and meter identification: Ambuda's `vidyut-chandas` (Rust with Python bindings; its own authors
call it experimental and not state-of-the-art), Terdalkar's Chandojñānam (arXiv:2209.14924), and
`hrishikeshrt/chanda` (pip-installable, 200+ meter database). None implements generative
*prastāra* enumeration, which is the part you want. Interoperate for scansion; build enumeration
and the index↔pattern pair yourself. **[survey]**

**Adjacent, culture-agnostic, worth reading for API shape.** Nick Montfort, *Exploratory
Programming for the Arts and Humanities* (MIT, 2016; 2nd ed. 2021) and ppg256; Allison Parrish's
libraries; Leonard Richardson's `olipy` (Queneau assembly and other Oulipian methods); Kate
Compton's Tracery; RiTa.js; the Corpora Project. These descend from one Western avant-garde
lineage and are not organised as a historical catalogue — precisely the difference worth
articulating in the README.

**Thin or hobbyist; do not depend on.** I Ching libraries are numerous but small
(urschrei/hexagrams, ratchetcat/i-ching, zzkt/i-ching, berisberis/py-ching, a Taixuanjing package
under the `iching` topic); gematria repositories are mostly calculators with no serious *tzeruf*
engine; Ifá repositories are hobbyist only.

**Nonexistent.** No public Denckring implementation or interactive simulator, despite the
device's fame in electronic-literature circles. No cross-tradition framework of any kind. Both
negatives are well supported but bounded by search.

**New primary sources for the Jean Paul layer. [survey]**
- *Jean Paul: Exzerpte. Digitale Edition* (Arbeitsstelle Jean-Paul-Edition, Würzburg;
  jp-exzerpte.uni-wuerzburg.de) — reported as over 12,000 manuscript pages and more than 100,000
  entries. Rights caveat: the transcription carries its own rights distinct from the
  public-domain manuscript. Contact the Arbeitsstelle before any distribution.
- Historisch-kritische Ausgabe, II. Abteilung (Nachlass), **Bd. 9: *Einfälle, Bausteine,
  Erfindungen*** (De Gruyter; text 2020, commentary 9.3). Kilcher in 2003 could only note it as
  announced. Reported to contain Jean Paul's own rules for the *Fabelarchitektur* of the novels —
  potentially author-stated procedures rather than reconstructions. Highest-value lead here.
- Michael Will, *Findbuch zu Jean Pauls Exzerpten* (Königshausen & Neumann, 2021) — reported as
  the first study of the "Exzerptenexzerpte" and the register's own register.
- Andrea Krauß, "Sammeln – Exzerpte – Konstellation. Jean Pauls literarische Kombinatorik",
  *Monatshefte* 105.2 (2013): 291–314.

---

## 11. Positioning, and what would falsify it

The project can defensibly claim first-of-kind: a cross-cultural, implementable catalogue of
combinatorial procedures does not appear to exist in any language. That is a stronger claim than
the project has made before, so it needs falsification conditions rather than confidence.

- **Weakens to "most comprehensive"** if a multi-tradition catalogue with executable specs turns
  up in the DH or electronic-literature literature.
- **The scholarly half narrows to the code layer only** if a monograph appears integrating
  Sanskrit, Chinese, European and African combinatorics in one formal frame.
- **The Denckring priority claim dies** the moment someone publishes an implementation. It is the
  most exposed of the three, because the device is well known and the specification is public. If
  priority matters, build it early; if not, don't let it drive the order.

If this gets written up, Cashner's JCMS article is the template: a device, its specification, its
implementation, and the reasoning connecting them, in one peer-reviewed venue. The comparative
frame in §4 is the novel part; the individual implementations are the evidence that it is
operational rather than rhetorical.

Natural interlocutors: Andrew Cashner (implementation methodology, code released); the
Ambuda/vidyut maintainers (Sanskrit interoperability); Andreas Kilcher at ETH Zürich, whose 1998
Kabbalah book and 2003 Habilitationsschrift together span two of the six traditions; Siegfried
Zielinski at UdK Berlin, whose *Variantology* series is the closest existing attempt at the
global frame.

---

## 12. Suggested order

1. **Muhmal mask as a schema field** (§2.2). Smallest change, widest reach, and the kill-criterion
   test for the instrument layer.
2. **Address space and index↔pattern protocol**, with prastāra as the reference implementation and
   the naṣṭa/uddiṣṭa citation attached (§2.3, §4). Three of the four primitives hang off this.
3. **Decide the layer split before adding any instrument-side entry** (§3). Adding temurah or Ifá
   to a flat collection with a 500 target quietly breaks the denominator, and unwinding it later
   is worse than deciding now.
4. **Hemeling** (§2.1). Highest value per unit effort on the Verfahren side, and its compound
   constraint exercises whatever multi-stage validation the harness has.
5. **Letterwechsel, Versus palindromus, Anagrammata.** Cheap, and they tidy the anagram family
   under Leibniz's own taxonomy.
6. **The Jean Paul split** (§9), if `Ideenwuerfeln` is still monolithic. Before the corpus layer
   hardens.
7. **Denckring**, if and only if priority matters (§11). Otherwise it is just another product-kind
   entry.
8. **Yijing and Taixuanjing.** Trivial base-2 and base-3 encodings; their value is populating the
   address-space schema with three radices and forcing the `ordering` field to be real.
9. **`transform` kind with temurah**, round-trip identity as the test. Validates the instrument
   layer end to end.
10. **Corpus-derived rings.** No scholarship required; the only genuinely contemporary capability
    in the set.
11. **Ifá and the geomantic tableau**, then **al-Khalīl** and **tzeruf** — for the last two the
    attestation data is the bottleneck, not the mechanism.
12. **`sequence` kind and backtracking**, last. Largest engineering effort, least historical
    urgency, but it carries the one publishable comparative finding (§4).

Blocked: Reimlexikon on rhyme data. Description-only: renvois, zāʾirja, Novalis without an LM
backend.

---

## 13. Explicitly not proposed

The following appear prominently in Kilcher and should stay out of the generator layer. They are
*Schreibweisen* with no specifiable rule, and forcing a generator onto them is a category error.
All remain legitimate as description-only catalogue entries.

- **Witz** and **Assoziation** (pp. 390–401) — the productive step is human recognition of hidden
  similarity. The project's own Ideenwürfeln reconstruction already reached this; do not
  relitigate it.
- **Arabeske** as an encyclopedic Schreibweise (Schlegel, pp. 427–431).
- **Montage / Allegoristik** (Benjamin, Arno Schmidt's Zettel, pp. 436–461).
- **Der Exkurs** (the "Exkurs über den Exkurs", p. 136) — digression is describable as a rule
  ("interrupt at defined points, insert material from another domain") but Kilcher does not
  specify the points, and inventing them would be reconstruction presented as author-stated.

Kilcher's own three paradigms (*Litteratur* / *Alphabet* / *Textur*) are a possible second facet
for browsing, sourced to a citable Habilitationsschrift. But they are **epochal**: a procedure's
paradigm depends on when it was practised, so a modern Oulipian revival of a Baroque device lands
in a different bucket than the original. That needs a per-instance rather than per-entry tag, or
the axis should be dropped. ADR before adoption, not after.

---

## 14. Honesty inventory

Every item here is a place where shipping a confident falsehood would be easy.

- **Denckring totals** — three-way conflict (§7). Compute; record the rest as disputed.
- **The Leibniz attribution for 97,209,600** — unverified, and prestigious enough to be dangerous.
- **zāʾirja → Llull** — contested, chronology against it, pro-transmission sources skew
  non-peer-reviewed. Bonner's position needs verifying against the Brill text.
- **Africa → geomancy → Leibniz** — hypothesis, evidence weak, and the "weak" judgement is a
  critic's not Eglash's.
- **Prastāra convention** — low-order end and symbol mapping vary. State the choice.
- **Yijing ordering** — natural binary is what the arithmetic produces; King Wen is a lookup
  table. If you ship King Wen, ship it from a source.
- **Ifá odu ordering** — the 16×16 structure is stable, the sequence is not.
- **Denckring plate pagination** — Zweyter Theil p. 517, not Dritter Theil. Confirm physically.
- **Workbench corpora** — the German morpheme rings, excerpt drawer, article set, Arabic
  attestation marks and renga imagery are all synthetic and labelled as such on their plates. Do
  not lift them into the package as data. The Llull alphabet and the Hebrew letters are
  historical.
- **Jean Paul digital edition** — transcription rights are distinct from the manuscript's
  public-domain status.
- **"First-of-kind"** — defensible but bounded by search (§11).
- **The DIA-LOGOS catalogue** — whether it contains a dedicated chapter on any specific
  non-European device was not confirmed. Check before citing it as precedent for the comparative
  frame.
- **OCR** — the Kilcher scan's text layer has systematic errors (*det* for *der*, *untet* for
  *unter*), and the file has a structural defect around p. 481. Search on distinctive nouns, not
  function words; inspect that page visually.

---

## 15. Open questions

- Does the 500 target count entries or generators? Decides whether §3 is bookkeeping or
  philosophy.
- Is a language-model backend in scope? Determines whether `transfer` survives at all.
- Does the test harness admit structural checks as verification? If yes, renvois becomes
  shippable and §1.3 is wrong about it.
- Does Denckring priority matter enough to reorder the work? §12 assumes not.
- Is the project willing to carry `influence` edges with proponents and skeptics as first-class
  data? §6 assumes yes; if not, those claims belong in entry notes as prose and nowhere else.

---

## Appendix — page map for Kilcher, *mathesis und poiesis* (Fink, 2003)

| Section | Pages | Relevance |
|---|---|---|
| Exkurs über den Exkurs | 136 | digression; not implementable |
| Enzyklopädische Ordnung des Reimlexikons | 231–244 | Reimlexikon (§1.2) |
| Diderot I / II: Theorie der Verweise | 252–265 | renvois (§1.3) |
| Stochastische Lektüre im Lexikonroman | 271–275 | reading-side procedure; unexamined |
| Satirische Wörterbücher | 289–309 | unexamined |
| Lullische Kybernetik | 357–369 | covered by facsimile research |
| Kombinatorische Poetik / Sprachalchemie | 370–378 | Letterwechsel, Hemeling, Leibniz's headings |
| Exzerptenenzyklopädik (Jean Paul) | 380–401 | the pipeline (§9); typology at 383ff |
| Kombinatorik, Assoziation, Witz | 390–395 | sampler constraint (§8); exclusions (§13) |
| Novalis, "Confusions-System" | 402–415 | synkritisch (§1.2) |
| Schlegel, Fragment und Totalität | 416–431 | exclusion |
| Montage (Benjamin, Arno Schmidt) | 436–461 | exclusion |
| Maschine / literarische Universalmaschinen | 462–481 | unexamined; scan defective near 481 |

Three sections were not examined closely and may repay a second pass: stochastic reading in the
Lexikonroman (271), the satirical dictionaries (289–309), and the universal-machine chapter
(462–481).
