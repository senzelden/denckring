# 31. A device is an address space, and it may know which of its readings are real

## Context

`docs/expansion_ideas/HANDOVER-denckring-method-zoo.md` surveys combinatorial devices
across six traditions and ranks what it proposes by value per unit of change. Its top
two are not new catalogue entries. They are schema changes to the devices already here,
and its own argument for them is that both arrived from traditions this project had not
modelled and both improve the generator side.

**A device has always been an odometer and never said so.** `Device.combinations`
multiplies the slot lengths, which is the size of an address space, and nothing else
treated it as one. There was no way to ask for the reading at a given index, or for the
index of a given reading — so the one structural fact every device in this catalogue
shares was expressible only as a count.

**A device produces garbage in bulk and had nowhere to say so.** `denckring.apply` spins
the rings and returns whatever comes up. Measured here: **0 of 20,000 spins of
Harsdörffer's rings is a word the German lexicon knows**, while **4.40% of German nouns
are spellable on those rings**. Both numbers are true and they are about different
questions; nothing in the schema could hold either.

**A device's published totals disagree, and the disagreement lived in a YAML comment.**
Three figures circulate for the Denckring — 82,944,000, 97,209,600, 101,606,400 — and
this package computes a fourth, 103,680,000, from the transcription it ships.

## Decision

**D1. `Device.at` and `Device.address` are the two directions of an index.** Piṅgala's
*Chandaḥśāstra* (c. 3rd–2nd c. BCE) names both — *naṣṭa* is address to pattern,
*uddiṣṭa* is pattern to address — which makes the odometer reading of these devices an
attested procedure rather than a modern gloss on one. `Device.radix` is the mixed base
they run in, and `combinations` is its product.

**The first slot is the most significant digit, and that is a choice.** Incrementing the
address turns the last ring, which is what an odometer does and what the reading order
suggests. Sources differ on which end of a *prastāra* row carries the low-order
position, so this is stated in the docstring and pinned by a test rather than presented
as *the* convention. A caller who wants the other numbering is doing arithmetic this
package does not do for them.

`address` raises for a reading the device cannot produce rather than returning a nearby
index, because a wrong address is indistinguishable from a right one.

**D2. `Device.mask` records which readings are attested, and holds rather than drops.**
Al-Khalīl ibn Aḥmad al-Farāhīdī's *Kitāb al-ʿAyn* (8th c.) enumerates every ordering of
a root's consonants and then marks which are realised and which are *muhmal*, neglected.
`unmarked_policy` defaults to `hold` because that is what al-Khalīl does: he does not
discard the neglected forms, and the distinction is the intellectual content of the
device rather than an implementation detail.

`mask.source` names a **capability**, not a file — `lexicon.words` is a question a pack
answers, and which pack is installed is the caller's business.

**D3. Reading the mask is opt-in, and refuses in both directions.**
`denckring apply` takes `attestation: ignore | mask`, defaulting to `ignore`. Asking for
`mask` on a device that declares none raises `InvalidParams`; asking it of a pack that
cannot answer raises `MissingCapability` naming the capability. Neither is silently
ignored.

The default is `ignore` so that a core-only install spins exactly as it always has.
Making the mask the default would give `denckring apply` a data dependency it has never
had, on the strength of a field in a YAML file.

**D4. `denckring` now spins `max_results` times rather than once.** A device that flags
which of its own outputs are real can only do so if it has produced more than one.
`apply` still reads `texts[0]`, which under `attestation: mask` is an attested word when
any spin found one — validation and generation in one pass, which is the handover's
argument for the mask.

**D5. `Device.disputed_totals` is a field, not a comment.** Each entry carries the value,
who asserts it, and a note. `combinations` stays computed. Recording is not adopting: the
97,209,600 that circulates most widely is not divisible by 144 and so cannot be a product
of rings of 12 and 120 at all, and a survey attributes it to Leibniz's own 1666
calculation without a primary citation. Adopting that attribution would mean asserting
Leibniz computed a number that is not the product of the rings as the same sources
describe them.

## Consequences

**The layer split is not taken here.** (It was taken on 2026-09-01; see ADR 0033.) The handover's §3 proposes splitting the collection into
`Verfahren` (run it, get text) and `Instrument` (the mechanism is faithfully formalised),
with separate counters and the 500 target belonging to the first. Nothing here needs that
decision: no catalogue entry is added, and both changes are to devices that already ship.
The handover's own kill criterion for that layer — "if after twenty `Instrument` entries
none has changed how a `Verfahren` entry is modelled, the layer is decoration" — names
these two as its test cases, and both came from the instrument side and improved the
generator side. That is evidence for the layer, gathered without committing to it.

**The mask is close to useless on the shipped rings, and the number is the point.** With
`drop`, a spin of Harsdörffer's rings returns nothing 20,000 times out of 20,000, so the
generator raises `DegenerateOutput`. That is not a defect to fix: it is what the device
does, and it is why `hold` is the default. The mask tests run against a synthetic
four-reading device, because a device that attests *sometimes* had to be built rather
than found.

**`Device.for_line` carries the mask and not the disputed totals.** A mask is a claim
about readings, which a line has; a disputed total is a claim about the whole device, and
attaching it to one line would assert that the literature disputed a number nobody
published.

**Two more devices could now declare a mask and do not.** `poesieautomat_2000` composes
lines rather than words, so `lexicon.words` is the wrong oracle for it, and no capability
in this project answers "is this a German sentence". Left undeclared rather than
declared with an oracle that cannot answer.

**The address protocol is unexercised by any procedure.** `at` and `address` are public
API with tests and no caller inside the package. That is deliberate — the handover wants
enumeration and the index pair as primitives the rest builds on — but it is a cost:
untested-in-anger code, kept honest only by its own round-trip property.

---

## Amendment, 2026-08-31: corpus-derived rings, and why they are not a catalogue row

`Device.from_text` builds a device whose rings are filled from a text the reader
supplies — the handover's §1.1 "corpus-derived rings", which it calls the only
genuinely contemporary capability in the whole set and the one needing no scholarship.
Structure fixed and enumerable, content input-dependent; `radix`, `at` and `address`
work on it unchanged, which is what D1 was for.

**It gets no catalogue entry, and the reason is a hole in the schema rather than a
judgement about the technique.** `attribution` offers `primary`, `reference` and
`traditional`, and `attested` offers `author-stated`, `codified` and `reconstruction`.
None of the six means *contemporary, with no source*. The handover says so itself: "no
historical precedent". Cataloguing it would put a technique this project invented beside
Harsdörffer's rings under provenance fields that would have to lie, in a catalogue whose
tests enforce those fields.

So it is a **device constructor plus `scripts/rings_from_text.py`**, and the devices it
writes are read by the rows that already exist, through the `DENCKRING_DEVICE_PATH`
cartridge mechanism `load` already documents. `denckring apply poesie_automat -p
device=notes` runs on rings drawn from `notes.txt` with no row claiming anything.

**This also answers a cost the Consequences above recorded.** `at` and `address` were
public API with tests and no caller; a derived device is enumerable by construction and
is the first thing that makes the pair worth having to someone outside this repository.

**Two costs of its own, stated.** The derivation must be total or a generator produces
output its own checker rejects, so ties are broken by first appearance and a test pins
that — a set iteration here would be a heisenbug in a row's verdict. And
`drop_commonest` is the whole stoplist: this package ships none, a real one is
per-language data, and dropping the *n* commonest types is the crude standard
substitute. At its default of 0 the rings fill with function words, which is a faithful
reading of the text and rarely the wanted one.

**If the schema ever grows a value for "contemporary, no source"** — the layer split in
§3 of the handover is where that would be decided — this is the first entry that would
want it. ADR 0033 took that decision and declined: an instrument must be *formalised and
sourced*, so a mechanism invented here fails its bar too, and `from_text` stays a
constructor catalogued on neither layer.
